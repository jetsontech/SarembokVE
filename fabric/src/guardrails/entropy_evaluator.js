/**
 * Antigravity Gemini Fabric - Sliding-Window Entropy & Semantic Loop Evaluator
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Tracks the last 5 agent-to-agent dialogue turns.
 * Computes Jaccard and cosine similarity approximations of successive outputs.
 * Flags loops if similarity across 3 turns exceeds 0.88.
 */

export class EntropyEvaluator {
  /**
   * @param {Object} [options]
   * @param {number} [options.windowSize=5]
   * @param {number} [options.consecutiveTurns=3]
   * @param {number} [options.threshold=0.88]
   */
  constructor(options = {}) {
    this.windowSize = options.windowSize ?? 5;
    this.consecutiveTurns = options.consecutiveTurns ?? 3;
    this.threshold = options.threshold ?? 0.88;
  }

  /**
   * Tokenize text into normalized n-grams (1-gram and 2-gram)
   * @param {string} text
   * @returns {Set<string>}
   */
  tokenizeToNGrams(text) {
    if (!text || typeof text !== 'string') return new Set();
    const clean = text.toLowerCase().replace(/[^\w\s]/g, ' ').trim();
    const tokens = clean.split(/\s+/).filter(Boolean);
    const ngrams = new Set(tokens);

    for (let i = 0; i < tokens.length - 1; i++) {
      ngrams.add(`${tokens[i]}_${tokens[i + 1]}`);
    }

    return ngrams;
  }

  /**
   * Compute Jaccard similarity between two token sets
   * @param {Set<string>} setA
   * @param {Set<string>} setB
   * @returns {number} Value between 0.0 and 1.0
   */
  calculateJaccardSimilarity(setA, setB) {
    if (setA.size === 0 && setB.size === 0) return 1.0;
    if (setA.size === 0 || setB.size === 0) return 0.0;

    let intersectionCount = 0;
    for (const item of setA) {
      if (setB.has(item)) {
        intersectionCount++;
      }
    }

    const unionCount = setA.size + setB.size - intersectionCount;
    return unionCount === 0 ? 0.0 : intersectionCount / unionCount;
  }

  /**
   * Compute token frequency vector for cosine similarity approximation
   * @param {string} text
   * @returns {Map<string, number>}
   */
  getTermFrequencies(text) {
    const map = new Map();
    if (!text || typeof text !== 'string') return map;
    const tokens = text.toLowerCase().replace(/[^\w\s]/g, ' ').split(/\s+/).filter(Boolean);
    for (const t of tokens) {
      map.set(t, (map.get(t) || 0) + 1);
    }
    return map;
  }

  /**
   * Approximate cosine similarity between two texts
   * @param {string} textA
   * @param {string} textB
   * @returns {number}
   */
  calculateCosineSimilarity(textA, textB) {
    const freqA = this.getTermFrequencies(textA);
    const freqB = this.getTermFrequencies(textB);

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (const [, count] of freqA) normA += count * count;
    for (const [, count] of freqB) normB += count * count;

    if (normA === 0 || normB === 0) return 0.0;

    for (const [term, countA] of freqA) {
      if (freqB.has(term)) {
        dotProduct += countA * freqB.get(term);
      }
    }

    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  /**
   * Compute semantic index (cosine-similarity approximation or Jaccard semantic index)
   * @param {string} textA
   * @param {string} textB
   * @returns {number}
   */
  computeSemanticIndex(textA, textB) {
    const jaccard = this.calculateJaccardSimilarity(
      this.tokenizeToNGrams(textA),
      this.tokenizeToNGrams(textB)
    );
    const cosine = this.calculateCosineSimilarity(textA, textB);
    // Take the maximum of cosine approximation and Jaccard semantic index
    return Number(Math.max(cosine, jaccard).toFixed(4));
  }

  /**
   * Evaluate sliding window for repetitive agent loops
   * @param {Array<{agent_id: string, output_payload: string}>} recentTurns
   * @returns {{loopDetected: boolean, maxSimilarity: number, agentId: string|null, reason: string|null}}
   */
  evaluateTurns(recentTurns) {
    if (!recentTurns || recentTurns.length < this.consecutiveTurns) {
      return { loopDetected: false, maxSimilarity: 0, agentId: null, reason: null };
    }

    // Examine turns within window (up to windowSize)
    const window = recentTurns.slice(-this.windowSize);

    // Track pairwise similarities between consecutive turns of same or adjacent agent dialogues
    let highSimilarityRun = 0;
    let maxSim = 0;
    let offendingAgentId = null;

    const extractText = (turn) => {
      const raw = turn.payload ?? turn.output_payload ?? '';
      if (typeof raw === 'string') {
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === 'object') {
            if (parsed.result !== undefined) return typeof parsed.result === 'string' ? parsed.result : JSON.stringify(parsed.result);
            if (parsed.output !== undefined) return typeof parsed.output === 'string' ? parsed.output : JSON.stringify(parsed.output);
          }
        } catch {}
        return raw;
      }
      if (typeof raw === 'object' && raw !== null) {
        if (raw.result !== undefined) return typeof raw.result === 'string' ? raw.result : JSON.stringify(raw.result);
        if (raw.output !== undefined) return typeof raw.output === 'string' ? raw.output : JSON.stringify(raw.output);
        return JSON.stringify(raw);
      }
      return String(raw);
    };

    for (let i = 1; i < window.length; i++) {
      const current = window[i];
      const previous = window[i - 1];

      const currentText = extractText(current);
      const prevText = extractText(previous);

      const sim = this.computeSemanticIndex(currentText, prevText);
      if (sim > maxSim) {
        maxSim = sim;
      }

      if (sim >= this.threshold) {
        highSimilarityRun++;
        offendingAgentId = current.sender_agent_id || current.agent_id;

        // If high similarity persists across consecutiveTurns (e.g. 3 turns)
        if (highSimilarityRun >= (this.consecutiveTurns - 1)) {
          return {
            loopDetected: true,
            maxSimilarity: maxSim,
            agentId: offendingAgentId,
            reason: `Semantic loop detected: similarity ${maxSim} >= ${this.threshold} across ${this.consecutiveTurns} successive dialogue turns.`
          };
        }
      } else {
        highSimilarityRun = 0;
      }
    }

    return {
      loopDetected: false,
      maxSimilarity: maxSim,
      agentId: null,
      reason: null
    };
  }
}
