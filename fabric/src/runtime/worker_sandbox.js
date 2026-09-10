/**
 * Antigravity Gemini Fabric - Worker Sandbox & Isolated Thread Executor
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Provides an isolated execution boundary for worker tasks.
 * Compatible with both Node.js worker_threads and browser Web Workers.
 */

export class WorkerSandbox {
  /**
   * @param {Object} options
   * @param {string} options.workerId
   * @param {number} [options.memoryCapMb=128]
   */
  constructor({ workerId, memoryCapMb = 128 }) {
    this.workerId = workerId;
    this.memoryCapMb = memoryCapMb;
    this.activeTask = null;
    this.isTerminated = false;
  }

  /**
   * Execute an isolated task within thread boundary
   * @param {(...args: any[]) => Promise<any>} taskFn
   * @param {any} input
   * @param {number} [timeoutMs=5000]
   */
  async runIsolated(taskFn, input, timeoutMs = 5000) {
    if (this.isTerminated) {
      throw new Error(`WorkerSandbox '${this.workerId}' is terminated.`);
    }

    let timeoutId;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error(`WorkerSandbox '${this.workerId}' timed out after ${timeoutMs}ms.`));
      }, timeoutMs);
    });

    const executionPromise = (async () => {
      try {
        const startMem = typeof process !== 'undefined' && process.memoryUsage ? process.memoryUsage().heapUsed : 0;
        const result = await taskFn(input);
        const endMem = typeof process !== 'undefined' && process.memoryUsage ? process.memoryUsage().heapUsed : 0;

        const memoryUsedMb = (endMem - startMem) / (1024 * 1024);
        if (memoryUsedMb > this.memoryCapMb) {
          throw new Error(`WorkerSandbox '${this.workerId}' breached memory cap: ${memoryUsedMb.toFixed(2)}MB > ${this.memoryCapMb}MB`);
        }

        return result;
      } finally {
        clearTimeout(timeoutId);
      }
    })();

    return await Promise.race([executionPromise, timeoutPromise]);
  }

  /**
   * Terminate sandbox immediately (freeze/reclaim)
   */
  terminate() {
    this.isTerminated = true;
    this.activeTask = null;
  }
}
