from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.ai.memory import InMemoryProvider
from src.ai.router import AIRouter
from src.approval.approval_queue import create_content_review_item
from src.business_engine.manager import BusinessEngineStore, normalize_job_type
from src.orchestrator.registry import FactoryRegistry
from src.providers.gemini_cli_provider import GeminiCLIProvider
from src.workflow.enums import WorkflowState
from src.workflow.runner import WorkflowRunner

WORKFLOW_BINDINGS = {
    "note_article": "social.note_article",
    "sns_post": "social.x_post",
    "affiliate_publish": "",
    "gemini_note_article": "",
    "gemini_sns_post": "",
    "gemini_seo_article": "",
    "gemini_affiliate_description": "",
    "gemini_business_report": "",
}


@dataclass
class WorkerResult:
    job_id: str
    job_type: str
    status: str
    message: str
    workflow_name: str = ""
    output_ref: str = ""


class BusinessWorker:
    """Local Business Engine worker.

    The worker is deliberately local-first: it uses the configured virtual-first
    AIRouter and writes only local execution state/output files.
    """

    def __init__(
        self,
        store: BusinessEngineStore | None = None,
        *,
        registry: FactoryRegistry | None = None,
        workflow_store_dir: str | Path | None = None,
    ) -> None:
        self.store = store or BusinessEngineStore()
        self.registry = registry or FactoryRegistry()
        self.registry.auto_discover()
        self.workflow_store_dir = Path(workflow_store_dir) if workflow_store_dir else None

    def workflow_for_job(self, job_type: str) -> str:
        normalized = normalize_job_type(job_type)
        workflow_name = WORKFLOW_BINDINGS.get(normalized, "")
        if workflow_name and self.registry.get_workflow(workflow_name) is not None:
            return workflow_name
        return ""

    def execute_next(self, *, auto_retry: bool = True) -> WorkerResult | None:
        if auto_retry:
            self.queue_failed_retries()
        data = self.store.load()
        job = next(
            (
                j for j in data.get("scheduled_jobs", [])
                if j.get("status") in ("queued", "retry_queued")
            ),
            None,
        )
        if job is None:
            self.store.set_worker_state("idle", message="No queued jobs.")
            return None
        return self.execute_job(job["job_id"])

    def process_queue(self, limit: int = 10, *, auto_retry: bool = True) -> list[WorkerResult]:
        results: list[WorkerResult] = []
        for _ in range(max(limit, 0)):
            result = self.execute_next(auto_retry=auto_retry)
            if result is None:
                break
            results.append(result)
        return results

    def queue_failed_retries(self) -> int:
        data = self.store.load()
        count = 0
        for job in data.get("scheduled_jobs", []):
            if job.get("status") != "failed":
                continue
            attempts = int(job.get("attempts", 0))
            max_attempts = int(job.get("max_attempts", 3))
            if attempts >= max_attempts:
                continue
            job["status"] = "retry_queued"
            count += 1
        if count:
            self.store.save(data)
        return count

    def execute_job(self, job_id: str) -> WorkerResult:
        data = self.store.load()
        job = next((j for j in data.get("scheduled_jobs", []) if j.get("job_id") == job_id), None)
        if job is None:
            return WorkerResult(job_id=job_id, job_type="", status="failed", message="Job not found.")

        job_type = normalize_job_type(job.get("job_type", ""))
        self.store.set_worker_state(
            "running",
            current_job_id=job_id,
            current_job_title=job.get("title", ""),
            message="Executing local job.",
        )
        self.store.update_job_status(job_id, "running")

        try:
            if job.get("payload", {}).get("force_fail"):
                raise RuntimeError(str(job.get("payload", {}).get("fail_message") or "Forced local failure."))

            if job_type.startswith("gemini_"):
                result = self._execute_gemini_cli(job)
                self.store.update_job_status(job_id, "completed")
                self.store.record_execution(job_id, "completed", result.message, result.output_ref)
                self.store.set_worker_state("idle", message=result.message)
                return result

            workflow_name = self.workflow_for_job(job_type)
            if workflow_name and job.get("payload", {}).get("use_workflow", True):
                result = self._execute_workflow(job, workflow_name)
            else:
                result = self._execute_local(job, workflow_name)

            self.store.update_job_status(job_id, "completed")
            self.store.record_execution(job_id, "completed", result.message, result.output_ref)
            self.store.set_worker_state("idle", message=result.message)
            return result
        except Exception as exc:
            message = str(exc)
            self.store.update_job_status(job_id, "failed", message)
            self.store.record_execution(job_id, "failed", message)
            self.store.set_worker_state("idle", message=message)
            return WorkerResult(job_id=job_id, job_type=job_type, status="failed", message=message)

    def _execute_gemini_cli(self, job: dict[str, Any]) -> WorkerResult:
        job_id = job["job_id"]
        job_type = normalize_job_type(job.get("job_type", ""))
        payload = job.get("payload", {}) or {}
        prompt = payload.get("prompt") or self._runtime_prompt(job)
        self.store.update_runtime_queue_status(job_id, "running")
        provider = GeminiCLIProvider(
            timeout_seconds=int(payload.get("timeout_seconds", 60)),
            retries=int(payload.get("retries", 1)),
        )
        cli_result = provider.execute_prompt(prompt)
        output_ref = ""
        if cli_result.ok:
            output_ref = self._write_runtime_output(job, cli_result.response)
            review = create_content_review_item(
                title=job.get("title", "Generated content"),
                content=cli_result.response,
                content_type=_approval_content_type(job_type),
                source_job_id=job_id,
            )
            self.store.update_runtime_queue_status(job_id, "completed", output_ref)
            self.store.record_runtime_result(
                job_id,
                job_type,
                "completed",
                duration_ms=cli_result.duration_ms,
                input_tokens=cli_result.input_tokens,
                output_tokens=cli_result.output_tokens,
                output_ref=output_ref,
            )
            return WorkerResult(
                job_id=job_id,
                job_type=job_type,
                status="completed",
                message=f"Completed Gemini CLI runtime job and queued review: {review['id']}",
                workflow_name="gemini_cli",
                output_ref=output_ref,
            )

        self.store.update_runtime_queue_status(job_id, "failed")
        self.store.record_runtime_result(
            job_id,
            job_type,
            "failed",
            duration_ms=cli_result.duration_ms,
            input_tokens=cli_result.input_tokens,
            output_tokens=cli_result.output_tokens,
            error=cli_result.error,
        )
        raise RuntimeError(cli_result.error or "Gemini CLI runtime failed.")

    def _execute_workflow(self, job: dict[str, Any], workflow_name: str) -> WorkerResult:
        definition = self.registry.get_workflow(workflow_name)
        if definition is None:
            raise RuntimeError(f"Workflow not found: {workflow_name}")

        memory = InMemoryProvider()
        router = AIRouter(memory=memory)
        runner = WorkflowRunner(router=router, memory=memory, store_dir=self.workflow_store_dir)
        status = runner.run(definition, self._workflow_context(job))
        if status.state != WorkflowState.COMPLETED:
            raise RuntimeError(status.error or f"Workflow failed: {workflow_name}")
        return WorkerResult(
            job_id=job["job_id"],
            job_type=normalize_job_type(job.get("job_type", "")),
            status="completed",
            message=f"Completed via workflow: {workflow_name}",
            workflow_name=workflow_name,
            output_ref=status.workflow_id,
        )

    def _execute_local(self, job: dict[str, Any], workflow_name: str = "") -> WorkerResult:
        job_type = normalize_job_type(job.get("job_type", ""))
        title = job.get("title", "Untitled job")
        message = f"Completed local {job_type} job: {title}"
        return WorkerResult(
            job_id=job["job_id"],
            job_type=job_type,
            status="completed",
            message=message,
            workflow_name=workflow_name,
            output_ref=f"local://business-engine/{job['job_id']}",
        )

    def _write_runtime_output(self, job: dict[str, Any], response: str) -> str:
        out_dir = Path("output") / "business_engine" / "runtime"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{job['job_id']}_{normalize_job_type(job.get('job_type', 'runtime'))}.md"
        path.write_text(response, encoding="utf-8")
        return str(path)

    @staticmethod
    def _runtime_prompt(job: dict[str, Any]) -> str:
        title = job.get("title", "AIOS runtime job")
        job_type = normalize_job_type(job.get("job_type", ""))
        prompts = {
            "gemini_note_article": f"Write a practical note article about: {title}",
            "gemini_sns_post": f"Write a concise SNS post about: {title}",
            "gemini_seo_article": f"Write an SEO article outline about: {title}",
            "gemini_affiliate_description": f"Write an affiliate product description about: {title}",
            "gemini_business_report": f"Write a short business report about: {title}",
        }
        return prompts.get(job_type, f"Generate business content for: {title}")

    @staticmethod
    def _workflow_context(job: dict[str, Any]) -> dict[str, Any]:
        payload = job.get("payload", {}) or {}
        title = job.get("title", "")
        return {
            "topic": payload.get("topic") or title,
            "target": payload.get("target", "AIOS beta users"),
            "tone": payload.get("tone", "practical"),
            "keywords": payload.get("keywords", "AIOS, automation, local-first"),
            "brand_name": payload.get("brand_name", "AIOS"),
            "job_id": job.get("job_id", ""),
        }


def _approval_content_type(job_type: str) -> str:
    return {
        "gemini_note_article": "note_article",
        "gemini_sns_post": "sns_post",
        "gemini_seo_article": "seo_article",
        "gemini_affiliate_description": "affiliate_description",
        "gemini_business_report": "business_report",
    }.get(job_type, "business_report")
