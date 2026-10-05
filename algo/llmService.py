import time
import threading
import uuid

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from queue import PriorityQueue
from typing import Optional, Iterator


# ============================================================
# 1. DATA MODELS
# ============================================================

@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class JobStatus(Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Job:
    id: str
    request: LLMRequest
    status: JobStatus = JobStatus.QUEUED
    result: Optional[LLMResponse] = None
    error: Optional[str] = None
    idempotency_key: Optional[str] = None


# ============================================================
# 2. LLM PROVIDER
# ============================================================

class LLMProvider(ABC):

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    def stream(self, request: LLMRequest) -> Iterator[str]:
        pass


# ------------------------------------------------------------
# Mock provider
# ------------------------------------------------------------

class MockProvider(LLMProvider):

    def __init__(self, name: str):
        self.name = name

    def generate(self, request: LLMRequest) -> LLMResponse:
        print(f"[{self.name}] generating...")

        # Simulate API latency
        time.sleep(1)

        return LLMResponse(
            content=f"Response from {self.name}: {request.prompt}",
            model=request.model,
            input_tokens=len(request.prompt.split()),
            output_tokens=10,
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        words = (
            f"Streaming response from {self.name}: "
            f"{request.prompt}"
        ).split()

        for word in words:
            time.sleep(0.2)
            yield word + " "


# ============================================================
# 3. PROVIDER ROUTER
# ============================================================

class ProviderRouter:

    def __init__(self, providers: dict[str, LLMProvider]):
        self.providers = providers

    def get_provider(self, model: str) -> LLMProvider:
        provider = self.providers.get(model)

        if provider is None:
            raise ValueError(
                f"No provider configured for model: {model}"
            )

        return provider


# ============================================================
# 4. CACHE
# ============================================================

class LLMCache(ABC):

    @abstractmethod
    def get(self, key: str) -> Optional[LLMResponse]:
        pass

    @abstractmethod
    def put(self, key: str, response: LLMResponse) -> None:
        pass


class InMemoryLLMCache(LLMCache):

    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[LLMResponse]:
        with self.lock:
            return self.cache.get(key)

    def put(self, key: str, response: LLMResponse) -> None:
        with self.lock:
            self.cache[key] = response


# ============================================================
# 5. RATE LIMITER
# ============================================================

class RateLimitStrategy(ABC):

    @abstractmethod
    def allow(self, key: str) -> bool:
        pass


class TokenBucket:

    def __init__(
        self,
        capacity: int,
        refill_rate: float
    ):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()

        self.lock = threading.Lock()

    def consume(self) -> bool:

        with self.lock:

            now = time.monotonic()

            elapsed = now - self.last_refill

            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )

            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            return False


class TokenBucketRateLimiter(RateLimitStrategy):

    def __init__(
        self,
        capacity: int,
        refill_rate: float
    ):
        self.capacity = capacity
        self.refill_rate = refill_rate

        self.buckets = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:

        with self.lock:

            if key not in self.buckets:
                self.buckets[key] = TokenBucket(
                    self.capacity,
                    self.refill_rate
                )

            bucket = self.buckets[key]

        return bucket.consume()


# ============================================================
# 6. RETRY POLICY
# ============================================================

class RetryPolicy(ABC):

    @abstractmethod
    def should_retry(
        self,
        attempt: int,
        error: Exception
    ) -> bool:
        pass

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        pass


class ExponentialBackoffRetry(RetryPolicy):

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def should_retry(
        self,
        attempt: int,
        error: Exception
    ) -> bool:

        # In production, inspect the actual exception
        # and retry only transient failures.
        return attempt <= self.max_retries

    def get_delay(self, attempt: int) -> float:

        return self.base_delay * (2 ** (attempt - 1))


# ============================================================
# 7. CIRCUIT BREAKER
# ============================================================

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 10
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.failure_count = 0
        self.last_failure_time = None

        self.state = CircuitState.CLOSED

        self.lock = threading.Lock()

    def allow_request(self) -> bool:

        with self.lock:

            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:

                elapsed = (
                    time.monotonic()
                    - self.last_failure_time
                )

                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True

                return False

            # HALF_OPEN
            return True

    def record_success(self):

        with self.lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def record_failure(self):

        with self.lock:

            self.failure_count += 1
            self.last_failure_time = time.monotonic()

            if (
                self.failure_count
                >= self.failure_threshold
            ):
                self.state = CircuitState.OPEN


# ============================================================
# 8. CONCURRENCY LIMITER
# ============================================================

class ConcurrencyLimiter:

    def __init__(self, max_concurrent: int):
        self.semaphore = threading.Semaphore(
            max_concurrent
        )

    def acquire(self):
        self.semaphore.acquire()

    def release(self):
        self.semaphore.release()


# ============================================================
# 9. PROVIDER EXECUTOR
# ============================================================

class ProviderExecutor:

    def __init__(
        self,
        provider: LLMProvider,
        retry_policy: RetryPolicy,
        circuit_breaker: CircuitBreaker,
        concurrency_limiter: ConcurrencyLimiter,
    ):
        self.provider = provider
        self.retry_policy = retry_policy
        self.circuit_breaker = circuit_breaker
        self.concurrency_limiter = concurrency_limiter

    def execute(
        self,
        request: LLMRequest
    ) -> LLMResponse:

        attempt = 0

        while True:

            if not self.circuit_breaker.allow_request():
                raise RuntimeError(
                    "Circuit breaker is OPEN"
                )

            self.concurrency_limiter.acquire()

            try:

                attempt += 1

                response = self.provider.generate(
                    request
                )

                self.circuit_breaker.record_success()

                return response

            except Exception as error:

                self.circuit_breaker.record_failure()

                if not self.retry_policy.should_retry(
                    attempt,
                    error
                ):
                    raise

                delay = self.retry_policy.get_delay(
                    attempt
                )

            finally:

                self.concurrency_limiter.release()

            # Don't hold concurrency slot while sleeping.
            time.sleep(delay)

    def stream(
        self,
        request: LLMRequest
    ) -> Iterator[str]:

        if not self.circuit_breaker.allow_request():
            raise RuntimeError(
                "Circuit breaker is OPEN"
            )

        self.concurrency_limiter.acquire()

        try:

            for chunk in self.provider.stream(request):
                yield chunk

            self.circuit_breaker.record_success()

        except Exception:

            self.circuit_breaker.record_failure()
            raise

        finally:

            self.concurrency_limiter.release()


# ============================================================
# 10. JOB STORE
# ============================================================

class JobStore:

    def __init__(self):

        self.jobs: dict[str, Job] = {}

        self.idempotency_map: dict[str, str] = {}

        self.lock = threading.Lock()

    def create(
        self,
        job: Job
    ) -> bool:

        with self.lock:

            if (
                job.idempotency_key
                and job.idempotency_key in self.idempotency_map
            ):
                return False

            self.jobs[job.id] = job

            if job.idempotency_key:
                self.idempotency_map[
                    job.idempotency_key
                ] = job.id

            return True

    def get(self, job_id: str) -> Optional[Job]:

        with self.lock:
            return self.jobs.get(job_id)

    def get_by_idempotency_key(
        self,
        key: str
    ) -> Optional[Job]:

        with self.lock:

            job_id = self.idempotency_map.get(key)

            if job_id is None:
                return None

            return self.jobs.get(job_id)

    def update(
        self,
        job_id: str,
        **kwargs
    ):

        with self.lock:

            job = self.jobs.get(job_id)

            if job is None:
                return

            for key, value in kwargs.items():
                setattr(job, key, value)


# ============================================================
# 11. JOB QUEUE
# ============================================================

HIGH = 1
MEDIUM = 2
LOW = 3


class JobQueue:

    def __init__(self, max_size: int = 1000):

        self.queue = PriorityQueue(
            maxsize=max_size
        )

        self.sequence = 0
        self.lock = threading.Lock()

    def put(
        self,
        job_id: str,
        priority: int
    ):

        with self.lock:
            sequence = self.sequence
            self.sequence += 1

        self.queue.put(
            (
                priority,
                sequence,
                job_id
            )
        )

    def get(self):

        return self.queue.get()

    def task_done(self):

        self.queue.task_done()


# ============================================================
# 12. WORKER POOL
# ============================================================

class WorkerPool:

    def __init__(
        self,
        job_queue: JobQueue,
        job_store: JobStore,
        provider_executor: ProviderExecutor,
    ):

        self.job_queue = job_queue
        self.job_store = job_store
        self.provider_executor = provider_executor

        self.workers = []

        self.shutdown_event = threading.Event()

    def start(self, num_workers: int):

        for i in range(num_workers):

            worker = threading.Thread(
                target=self._worker_loop,
                name=f"worker-{i}"
            )

            worker.daemon = True
            worker.start()

            self.workers.append(worker)

    def _worker_loop(self):

        while not self.shutdown_event.is_set():

            try:
                priority, sequence, job_id = (
                    self.job_queue.get()
                )

                self._process(job_id)

            except Exception as e:

                print(
                    f"Worker error: {e}"
                )

            finally:

                self.job_queue.task_done()

    def _process(self, job_id: str):

        job = self.job_store.get(job_id)

        if job is None:
            return

        # If client cancelled while job was queued.
        if job.status == JobStatus.CANCELLED:
            return

        self.job_store.update(
            job_id,
            status=JobStatus.RUNNING
        )

        try:

            response = self.provider_executor.execute(
                job.request
            )

            self.job_store.update(
                job_id,
                status=JobStatus.SUCCESS,
                result=response
            )

        except Exception as e:

            self.job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(e)
            )

    def shutdown(self):

        self.shutdown_event.set()


# ============================================================
# 13. JOB SCHEDULER
# ============================================================

class JobScheduler:

    def __init__(
        self,
        job_store: JobStore,
        job_queue: JobQueue
    ):

        self.job_store = job_store
        self.job_queue = job_queue

    def submit(
        self,
        request: LLMRequest,
        priority: int = MEDIUM,
        idempotency_key: Optional[str] = None
    ) -> str:

        # First check existing idempotent request.
        if idempotency_key:

            existing = (
                self.job_store
                .get_by_idempotency_key(
                    idempotency_key
                )
            )

            if existing:
                return existing.id

        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            request=request,
            idempotency_key=idempotency_key
        )

        created = self.job_store.create(job)

        if not created:

            # Another request may have created
            # the same idempotency key concurrently.
            existing = (
                self.job_store
                .get_by_idempotency_key(
                    idempotency_key
                )
            )

            return existing.id

        try:

            self.job_queue.put(
                job_id,
                priority
            )

        except Exception as e:

            self.job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(e)
            )

            raise

        return job_id

    def cancel(self, job_id: str) -> bool:

        job = self.job_store.get(job_id)

        if job is None:
            return False

        if job.status == JobStatus.QUEUED:

            self.job_store.update(
                job_id,
                status=JobStatus.CANCELLED
            )

            return True

        # Running jobs require cooperative cancellation.
        return False


# ============================================================
# 14. MAIN LLM SERVICE
# ============================================================

class LLMService:

    def __init__(
        self,
        router: ProviderRouter,
        cache: LLMCache,
        rate_limiter: RateLimitStrategy,
        scheduler: JobScheduler,
        provider_executors: dict[str, ProviderExecutor],
    ):

        self.router = router
        self.cache = cache
        self.rate_limiter = rate_limiter
        self.scheduler = scheduler
        self.provider_executors = provider_executors

    # --------------------------------------------------------
    # Cache key
    # --------------------------------------------------------

    def _build_cache_key(
        self,
        request: LLMRequest
    ) -> str:

        return (
            f"{request.model}:"
            f"{request.temperature}:"
            f"{request.max_tokens}:"
            f"{request.prompt}"
        )

    # --------------------------------------------------------
    # Synchronous generation
    # --------------------------------------------------------

    def generate(
        self,
        user_id: str,
        request: LLMRequest
    ) -> LLMResponse:

        # 1. User/API rate limit
        if not self.rate_limiter.allow(user_id):
            raise RuntimeError(
                "Rate limit exceeded"
            )

        # 2. Cache
        cache_key = self._build_cache_key(request)

        cached = self.cache.get(cache_key)

        if cached is not None:
            print("Cache hit")
            return cached

        # 3. Select provider
        provider = self.router.get_provider(
            request.model
        )

        # 4. Execute
        executor = self.provider_executors[
            request.model
        ]

        response = executor.execute(request)

        # 5. Cache
        self.cache.put(
            cache_key,
            response
        )

        return response

    # --------------------------------------------------------
    # Streaming
    # --------------------------------------------------------

    def stream(
        self,
        user_id: str,
        request: LLMRequest
    ) -> Iterator[str]:

        if not self.rate_limiter.allow(user_id):
            raise RuntimeError(
                "Rate limit exceeded"
            )

        executor = self.provider_executors[
            request.model
        ]

        for chunk in executor.stream(request):
            yield chunk

    # --------------------------------------------------------
    # Async generation
    # --------------------------------------------------------

    def generate_async(
        self,
        user_id: str,
        request: LLMRequest,
        priority: int = MEDIUM,
        idempotency_key: Optional[str] = None
    ) -> str:

        if not self.rate_limiter.allow(user_id):
            raise RuntimeError(
                "Rate limit exceeded"
            )

        return self.scheduler.submit(
            request=request,
            priority=priority,
            idempotency_key=idempotency_key
        )

    # --------------------------------------------------------
    # Job status
    # --------------------------------------------------------

    def get_job(
        self,
        job_id: str
    ) -> Optional[Job]:

        return self.scheduler.job_store.get(
            job_id
        )

    # --------------------------------------------------------
    # Cancel job
    # --------------------------------------------------------

    def cancel_job(
        self,
        job_id: str
    ) -> bool:

        return self.scheduler.cancel(
            job_id
        )


# ============================================================
# 15. BUILD THE SYSTEM
# ============================================================

def build_service():

    # --------------------------------------------------------
    # Providers
    # --------------------------------------------------------

    openai = MockProvider("OpenAI")
    anthropic = MockProvider("Anthropic")

    providers = {
        "gpt-5": openai,
        "claude": anthropic,
    }

    router = ProviderRouter(providers)

    # --------------------------------------------------------
    # Provider executors
    # --------------------------------------------------------

    provider_executors = {}

    for model, provider in providers.items():

        retry_policy = ExponentialBackoffRetry(
            max_retries=2,
            base_delay=0.5
        )

        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10
        )

        concurrency_limiter = ConcurrencyLimiter(
            max_concurrent=5
        )

        provider_executors[model] = ProviderExecutor(
            provider=provider,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
            concurrency_limiter=concurrency_limiter
        )

    # --------------------------------------------------------
    # Cache
    # --------------------------------------------------------

    cache = InMemoryLLMCache()

    # --------------------------------------------------------
    # Rate limiter
    # --------------------------------------------------------

    rate_limiter = TokenBucketRateLimiter(
        capacity=10,
        refill_rate=1
    )

    # --------------------------------------------------------
    # Job system
    # --------------------------------------------------------

    job_store = JobStore()

    job_queue = JobQueue(
        max_size=100
    )

    scheduler = JobScheduler(
        job_store=job_store,
        job_queue=job_queue
    )

    # --------------------------------------------------------
    # Worker pool
    # --------------------------------------------------------

    # For this example we use one executor because all
    # workers eventually route to the requested provider.
    #
    # A production implementation would select the
    # ProviderExecutor based on job.request.model.

    class RoutingProviderExecutor:

        def execute(self, request):

            executor = provider_executors[
                request.model
            ]

            return executor.execute(request)

        def stream(self, request):

            executor = provider_executors[
                request.model
            ]

            return executor.stream(request)

    routing_executor = RoutingProviderExecutor()

    worker_pool = WorkerPool(
        job_queue=job_queue,
        job_store=job_store,
        provider_executor=routing_executor
    )

    worker_pool.start(
        num_workers=5
    )

    # --------------------------------------------------------
    # LLM Service
    # --------------------------------------------------------

    service = LLMService(
        router=router,
        cache=cache,
        rate_limiter=rate_limiter,
        scheduler=scheduler,
        provider_executors=provider_executors
    )

    return service, worker_pool


# ============================================================
# 16. DEMO
# ============================================================

if __name__ == "__main__":

    service, worker_pool = build_service()

    request = LLMRequest(
        prompt="Explain transformers",
        model="gpt-5",
        temperature=0.7,
        max_tokens=100
    )

    # --------------------------------------------------------
    # Synchronous request
    # --------------------------------------------------------

    print("\n--- SYNC REQUEST ---")

    response = service.generate(
        user_id="user-1",
        request=request
    )

    print(response.content)

    # Same request should hit cache.
    print("\n--- CACHE REQUEST ---")

    response = service.generate(
        user_id="user-1",
        request=request
    )

    print(response.content)

    # --------------------------------------------------------
    # Streaming
    # --------------------------------------------------------

    print("\n--- STREAMING ---")

    for chunk in service.stream(
        user_id="user-1",
        request=request
    ):
        print(chunk, end="", flush=True)

    print()

    # --------------------------------------------------------
    # Async job
    # --------------------------------------------------------

    print("\n--- ASYNC JOB ---")

    job_id = service.generate_async(
        user_id="user-1",
        request=request,
        priority=HIGH,
        idempotency_key="request-123"
    )

    print("Job ID:", job_id)

    # --------------------------------------------------------
    # Poll job
    # --------------------------------------------------------

    while True:

        job = service.get_job(job_id)

        print(
            "Job status:",
            job.status.value
        )

        if job.status in (
            JobStatus.SUCCESS,
            JobStatus.FAILED,
            JobStatus.CANCELLED
        ):
            break

        time.sleep(0.2)

    if job.status == JobStatus.SUCCESS:
        print(
            "Result:",
            job.result.content
        )

    # --------------------------------------------------------
    # Idempotency test
    # --------------------------------------------------------

    print("\n--- IDEMPOTENCY ---")

    job1 = service.generate_async(
        user_id="user-1",
        request=request,
        idempotency_key="same-request"
    )

    job2 = service.generate_async(
        user_id="user-1",
        request=request,
        idempotency_key="same-request"
    )

    print("Job 1:", job1)
    print("Job 2:", job2)

    assert job1 == job2

    print("Idempotency works")

    worker_pool.shutdown()