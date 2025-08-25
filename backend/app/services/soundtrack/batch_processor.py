"""Batch processing for efficient bulk operations"""

import asyncio
from typing import List, Dict, Any, Callable, Optional, TypeVar, Generic
from datetime import datetime
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BatchPriority(Enum):
    """Batch processing priority levels"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class BatchJob(Generic[T]):
    """Represents a batch processing job"""
    id: str
    items: List[T]
    processor: Callable
    priority: BatchPriority = BatchPriority.NORMAL
    max_retries: int = 3
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class BatchProcessor:
    """
    Efficient batch processor for bulk API operations.
    Handles 10,000+ zones with intelligent batching and parallel processing.
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        max_parallel: int = 10,
        queue_size: int = 1000,
        process_interval: float = 0.1
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items per batch
            max_parallel: Maximum parallel batch operations
            queue_size: Maximum queue size
            process_interval: Interval between batch processing (seconds)
        """
        self.batch_size = batch_size
        self.max_parallel = max_parallel
        self.queue_size = queue_size
        self.process_interval = process_interval
        
        # Processing queue with priority
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=queue_size)
        self._processing: Dict[str, BatchJob] = {}
        self._results: Dict[str, Any] = {}
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._semaphore = asyncio.Semaphore(max_parallel)
        
        # Metrics
        self.total_batches = 0
        self.processed_items = 0
        self.failed_items = 0
        self.average_batch_time = 0.0
        self._batch_times: List[float] = []
    
    async def start(self, num_workers: int = None):
        """Start batch processor workers"""
        if self._running:
            return
        
        self._running = True
        num_workers = num_workers or self.max_parallel
        
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"Started {num_workers} batch processor workers")
    
    async def stop(self):
        """Stop batch processor and wait for completion"""
        self._running = False
        
        # Wait for queue to be processed
        await self._queue.join()
        
        # Cancel workers
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("Batch processor stopped")
    
    async def _worker(self, name: str):
        """Worker coroutine for processing batches"""
        logger.debug(f"Batch worker {name} started")
        
        while self._running:
            try:
                # Get job from queue with timeout
                priority, job = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                
                # Process the batch
                async with self._semaphore:
                    await self._process_batch(job)
                
                self._queue.task_done()
                
                # Small delay between batches
                await asyncio.sleep(self.process_interval)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {name} error: {e}")
    
    async def _process_batch(self, job: BatchJob):
        """Process a single batch job"""
        start_time = datetime.utcnow()
        self._processing[job.id] = job
        
        try:
            logger.debug(f"Processing batch {job.id} with {len(job.items)} items")
            
            # Execute batch processor function
            results = await job.processor(job.items)
            
            # Store results
            self._results[job.id] = {
                "success": True,
                "results": results,
                "processed_at": datetime.utcnow(),
                "duration": (datetime.utcnow() - start_time).total_seconds()
            }
            
            # Update metrics
            self.total_batches += 1
            self.processed_items += len(job.items)
            self._update_batch_time((datetime.utcnow() - start_time).total_seconds())
            
            logger.info(f"Batch {job.id} completed: {len(job.items)} items in {self._results[job.id]['duration']:.2f}s")
            
        except Exception as e:
            logger.error(f"Batch {job.id} failed: {e}")
            
            self._results[job.id] = {
                "success": False,
                "error": str(e),
                "processed_at": datetime.utcnow(),
                "duration": (datetime.utcnow() - start_time).total_seconds()
            }
            
            self.failed_items += len(job.items)
            
        finally:
            del self._processing[job.id]
    
    def _update_batch_time(self, duration: float):
        """Update average batch processing time"""
        self._batch_times.append(duration)
        if len(self._batch_times) > 100:
            self._batch_times = self._batch_times[-100:]
        
        self.average_batch_time = sum(self._batch_times) / len(self._batch_times)
    
    async def submit_batch(
        self,
        job_id: str,
        items: List[Any],
        processor: Callable,
        priority: BatchPriority = BatchPriority.NORMAL
    ) -> str:
        """
        Submit items for batch processing.
        
        Args:
            job_id: Unique job identifier
            items: Items to process
            processor: Async function to process batch
            priority: Processing priority
        
        Returns:
            Job ID for tracking
        """
        job = BatchJob(
            id=job_id,
            items=items,
            processor=processor,
            priority=priority
        )
        
        # Add to priority queue (lower number = higher priority)
        await self._queue.put((10 - priority.value, job))
        
        logger.debug(f"Submitted batch {job_id} with {len(items)} items, priority {priority.name}")
        return job_id
    
    async def submit_bulk(
        self,
        items: List[Any],
        processor: Callable,
        job_prefix: str = "batch",
        priority: BatchPriority = BatchPriority.NORMAL
    ) -> List[str]:
        """
        Submit bulk items, automatically splitting into optimal batches.
        
        Args:
            items: All items to process
            processor: Async function to process each batch
            job_prefix: Prefix for job IDs
            priority: Processing priority
        
        Returns:
            List of job IDs
        """
        job_ids = []
        
        # Split items into batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            job_id = f"{job_prefix}_{i//self.batch_size}_{datetime.utcnow().timestamp()}"
            
            await self.submit_batch(job_id, batch, processor, priority)
            job_ids.append(job_id)
        
        logger.info(f"Submitted {len(job_ids)} batches for {len(items)} items")
        return job_ids
    
    async def wait_for_job(self, job_id: str, timeout: float = None) -> Dict[str, Any]:
        """
        Wait for a specific job to complete.
        
        Args:
            job_id: Job ID to wait for
            timeout: Maximum wait time in seconds
        
        Returns:
            Job results
        """
        start_time = datetime.utcnow()
        
        while job_id not in self._results:
            if timeout:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
            
            await asyncio.sleep(0.1)
        
        return self._results[job_id]
    
    async def wait_for_all(self, job_ids: List[str], timeout: float = None) -> Dict[str, Dict[str, Any]]:
        """
        Wait for multiple jobs to complete.
        
        Args:
            job_ids: List of job IDs to wait for
            timeout: Maximum wait time in seconds
        
        Returns:
            Dictionary of job results
        """
        tasks = [self.wait_for_job(job_id, timeout) for job_id in job_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            job_id: result if not isinstance(result, Exception) else {"success": False, "error": str(result)}
            for job_id, result in zip(job_ids, results)
        }
    
    def get_job_status(self, job_id: str) -> str:
        """Get current status of a job"""
        if job_id in self._results:
            return "completed"
        elif job_id in self._processing:
            return "processing"
        else:
            return "queued"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get batch processor metrics"""
        return {
            "queue_size": self._queue.qsize(),
            "processing_count": len(self._processing),
            "completed_count": len(self._results),
            "total_batches": self.total_batches,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "average_batch_time": self.average_batch_time,
            "workers_active": len(self._workers),
            "is_running": self._running
        }
    
    def clear_results(self, older_than_seconds: int = 3600):
        """Clear old results to free memory"""
        cutoff = datetime.utcnow()
        
        to_remove = []
        for job_id, result in self._results.items():
            if "processed_at" in result:
                age = (cutoff - result["processed_at"]).total_seconds()
                if age > older_than_seconds:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self._results[job_id]
        
        if to_remove:
            logger.info(f"Cleared {len(to_remove)} old job results")


class AdaptiveBatchProcessor(BatchProcessor):
    """
    Batch processor with adaptive batch sizing based on performance.
    Automatically adjusts batch size for optimal throughput.
    """
    
    def __init__(self, min_batch_size: int = 10, max_batch_size: int = 500, **kwargs):
        super().__init__(**kwargs)
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.optimal_batch_size = self.batch_size
        
        # Performance tracking
        self._batch_performance: Dict[int, List[float]] = {}
        self._last_adjustment = datetime.utcnow()
        self._adjustment_interval = 60  # seconds
    
    def _update_batch_time(self, duration: float):
        """Override to track performance by batch size"""
        super()._update_batch_time(duration)
        
        # Track performance for current batch size
        if self.batch_size not in self._batch_performance:
            self._batch_performance[self.batch_size] = []
        
        self._batch_performance[self.batch_size].append(duration)
        
        # Limit history
        if len(self._batch_performance[self.batch_size]) > 20:
            self._batch_performance[self.batch_size] = self._batch_performance[self.batch_size][-20:]
        
        # Adjust batch size periodically
        if (datetime.utcnow() - self._last_adjustment).total_seconds() > self._adjustment_interval:
            self._adjust_batch_size()
    
    def _adjust_batch_size(self):
        """Adjust batch size based on performance metrics"""
        if len(self._batch_performance) < 3:
            return  # Need more data
        
        # Calculate throughput for each batch size
        throughputs = {}
        for size, times in self._batch_performance.items():
            if times:
                avg_time = sum(times) / len(times)
                throughput = size / avg_time  # items per second
                throughputs[size] = throughput
        
        # Find optimal batch size
        if throughputs:
            optimal_size = max(throughputs, key=throughputs.get)
            
            # Apply change gradually
            if optimal_size > self.batch_size:
                self.batch_size = min(self.batch_size + 10, self.max_batch_size)
                logger.info(f"Increased batch size to {self.batch_size}")
            elif optimal_size < self.batch_size:
                self.batch_size = max(self.batch_size - 10, self.min_batch_size)
                logger.info(f"Decreased batch size to {self.batch_size}")
            
            self.optimal_batch_size = optimal_size
            self._last_adjustment = datetime.utcnow()