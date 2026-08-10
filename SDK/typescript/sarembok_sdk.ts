/**
 * Sarembok VE Production Edition — Official TypeScript SDK
 * Exposes all 12 Platform RPC Facets for External Web/Node Integrations.
 */

export class SarembokClient {
    private url: string;
    private ws: WebSocket | null = null;

    constructor(host: string = "127.0.0.1", port: number = 9000) {
        this.url = `ws://${host}:${port}`;
    }

    public async connect(): Promise<boolean> {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.url);
            this.ws.onopen = () => resolve(true);
            this.ws.onerror = (err) => reject(err);
        });
    }

    private async call(method: string, params: Record<string, any> = {}): Promise<any> {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            await this.connect();
        }
        return new Promise((resolve) => {
            const id = `sdk-${method.toLowerCase()}`;
            const handler = (event: MessageEvent) => {
                const data = JSON.parse(event.data);
                if (data.id === id) {
                    this.ws?.removeEventListener("message", handler);
                    resolve(data);
                }
            };
            this.ws?.addEventListener("message", handler);
            this.ws?.send(JSON.stringify({ jsonrpc: "2.0", id, method, params }));
        });
    }

    public async createAgent(agentId: string, displayName: string) {
        return this.call("CreateAgent", { agentId, displayName });
    }

    public async queryAgentState(agentId: string) {
        return this.call("QueryAgentState", { agentId });
    }

    public async injectPerception(agentId: string, perceptionJson: string) {
        return this.call("InjectPerception", { agentId, perception: perceptionJson });
    }

    public async evaluateDecision(agentId: string, actionId: string, riskScore: number, confidence: number) {
        return this.call("EvaluateDecision", { agentId, actionId, riskScore, confidence });
    }

    public async getCognitiveScorecard(agentId: string) {
        return this.call("GetCognitiveScorecard", { agentId });
    }

    public async queryWorldModel(filter: string = "all") {
        return this.call("QueryWorldModel", { filter });
    }

    public async createDelegation(sourceAgentId: string, targetAgentId: string, goalId: string) {
        return this.call("CreateDelegation", { sourceAgentId, targetAgentId, goalId });
    }

    public async getAuditTrail(agentId: string) {
        return this.call("GetAuditTrail", { agentId });
    }

    public async sendMessage(agentId: string, content: string) {
        return this.call("SendMessage", { agentId, content });
    }

    public async getEvents(agentId: string) {
        return this.call("GetEvents", { agentId });
    }

    public async getMetrics(agentId: string) {
        return this.call("GetMetrics", { agentId });
    }

    public async restoreState(agentId: string, walEntries: number = 0) {
        return this.call("RestoreState", { agentId, walEntries });
    }

    public close() {
        this.ws?.close();
    }
}
