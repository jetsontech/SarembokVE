"""Production control-plane guardrails for SarembokVE."""
from __future__ import annotations
import hashlib, hmac, json, os, re, threading, time
from collections import deque
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

ROLE_LEVEL = {"PUBLIC":0,"USER":1,"WORKER":2,"OPERATOR":3,"ADMIN":4,"MASTER":5,"SYSTEM":6}
USER_METHODS = {
 "GetRuntimeInfo","GetProviderMetrics","GetVisualEngineStatus","ListWorkers","ListTasks","ListProjects",
 "GetCurrentUser","GetFeedbackSummary","ListMemories","SearchMemories","ListDigitalHumanSessions",
 "GetDigitalHumanSession","ListMcpServers","GetGpuMarketplace","ListGpuRentals","GetVisionStatus",
 "GetAdminStatus","GetConversationHistory","GetRuntimeAuthority","GetRuntimeDiagnostics","SarembokChat","Chat",
 "SarembokDialogue","BrowserNavigate","BrowserScreenshot","BrowserRender","SubmitFeedback","StoreMemory",
 "DeleteMemory","CreateDigitalHumanSession","CloseDigitalHumanSession","SearchYouTube","ResolveMediaStream",
 "ProcessVisionFrame","SpatialVisualRecall","GenerateImage","SaveUserChatSession","ListUserChatSessions",
 "DeleteUserChatSession"
}
WORKER_METHODS = {"RegisterWorker","Heartbeat","ClaimTask","CompleteTask","FailTask","ExecuteComputeTask"}
OPERATOR_METHODS = {"CreateAgent","CreateProject","CreateTask","ScheduleCompute","InjectPerception","EvaluateDecision","CreateDelegation","SendMessage","RestoreState","PruneWorkers","ScaleWorkers","RegisterMcpServer"}
ADMIN_METHODS = {"AdminExecuteDirective","RentGpuNode"}
LOGIN_METHODS = {"AuthenticateMaster","AuthenticateSocialUser","VerifyAdminPasscode"}
CANCELLATION_METHODS = {"CancelActiveStream"}
METHOD_REQUIREMENTS = {**{m:"USER" for m in USER_METHODS}, **{m:"WORKER" for m in WORKER_METHODS}, **{m:"OPERATOR" for m in OPERATOR_METHODS}, **{m:"ADMIN" for m in ADMIN_METHODS}}
METHOD_REQUIREMENTS.update({m:"USER" for m in CANCELLATION_METHODS})
SECRET_KEYS = re.compile(r"(?i)(api[_-]?key|authorization|session[_-]?token|access[_-]?token|refresh[_-]?token|password|passcode|secret|worker[_-]?token|enrollment[_-]?token)")
SECRET_VALUES = re.compile(r"(?i)\b(?:sk-or-|sk-|gsk_|AIza)[A-Za-z0-9_.-]{12,}\b")

def token_fingerprint(v:str)->str: return hashlib.sha256(v.encode()).hexdigest()[:12] if v else ""
def scrub(v:Any)->Any:
    if isinstance(v,dict): return {k:"[REDACTED]" if SECRET_KEYS.search(str(k)) else scrub(x) for k,x in v.items()}
    if isinstance(v,list): return [scrub(x) for x in v]
    if isinstance(v,tuple): return tuple(scrub(x) for x in v)
    if isinstance(v,str): return SECRET_VALUES.sub("[REDACTED]",v)
    return v

class FixedWindowRateLimiter:
    def __init__(self,limit:int,window:float): self.limit=max(1,int(limit)); self.window=max(1.0,float(window)); self.events={}; self.lock=threading.Lock()
    def allow(self,key:str)->tuple[bool,int]:
        now=time.monotonic()
        with self.lock:
            q=self.events.setdefault(key,deque()); cutoff=now-self.window
            while q and q[0]<=cutoff:q.popleft()
            if len(q)>=self.limit:return False,max(1,int(q[0]+self.window-now))
            q.append(now)
            return True,0

class IdempotencyCache:
    def __init__(self,ttl:float=300,max_entries:int=5000): self.ttl=max(5,float(ttl)); self.max_entries=max(100,int(max_entries)); self.items={}; self.lock=threading.Lock()
    def get(self,subject,method,key):
        if not key:return None
        with self.lock:
            item=self.items.get((subject,method,key)); now=time.monotonic()
            if not item:return None
            if item[0]<=now:self.items.pop((subject,method,key),None); return None
            return dict(item[1])
    def put(self,subject,method,key,value):
        if not key:return
        with self.lock:
            if len(self.items)>=self.max_entries:self.items.pop(next(iter(self.items)))
            self.items[(subject,method,key)]=(time.monotonic()+self.ttl,dict(value))

@dataclass(frozen=True)
class Identity:
    role:str; subject:str; fingerprint:str=""

class ProductionGuard:
    def __init__(self):
        env=os.getenv
        self.auth_token=env("SAREMBOK_AUTH_TOKEN","").strip(); self.admin_token=env("SAREMBOK_ADMIN_TOKEN","").strip(); self.master_token=env("SAREMBOK_MASTER_TOKEN","").strip(); self.worker_enrollment_token=env("SAREMBOK_WORKER_ENROLLMENT_TOKEN","").strip()
        self.public_host=env("SAREMBOK_PUBLIC_HOST",env("SAREMBOK_SITE_ADDRESS","sarembok.com")).strip().lower()
        self.require_origin=env("SAREMBOK_REQUIRE_ORIGIN","true").strip().lower() not in {"0","false","no"}
        self.allow_originless_local=env("SAREMBOK_ALLOW_ORIGINLESS_LOCAL","true").strip().lower() in {"1","true","yes"}
        self.per_ip=FixedWindowRateLimiter(env("SAREMBOK_RATE_LIMIT_PER_IP","120"),env("SAREMBOK_RATE_LIMIT_WINDOW_SECONDS","60"))
        self.per_subject=FixedWindowRateLimiter(env("SAREMBOK_RATE_LIMIT_PER_SUBJECT","180"),env("SAREMBOK_RATE_LIMIT_SUBJECT_WINDOW_SECONDS","60"))
        self.idempotency=IdempotencyCache(env("SAREMBOK_IDEMPOTENCY_TTL_SECONDS","300"))
    @staticmethod
    def level(role): return ROLE_LEVEL.get(role,0)
    def client_key(self,ws):
        p=getattr(ws,"remote_address",None); return str(p[0] if isinstance(p,(tuple,list)) and p else p or "unknown")
    def allow_ip(self,ws):
        ok,retry=self.per_ip.allow(self.client_key(ws))
        if not ok: raise PermissionError(f"rate_limited_retry_after={retry}")
    def allow_subject(self,identity):
        ok,retry=self.per_subject.allow(identity.subject)
        if not ok: raise PermissionError(f"rate_limited_retry_after={retry}")
    def origin_allowed(self,ws):
        if not self.require_origin:return True
        headers=getattr(ws,"request_headers",None)
        if headers is None:
            request=getattr(ws,"request",None)
            headers=getattr(request,"headers",None) if request is not None else None
        if headers is None: return False
        raw_origin=str(headers.get("Origin","")).strip()
        if not raw_origin:
            host=str(headers.get("Host","")).strip().lower().rstrip("/")
            if host.count(":") == 1 and host.rsplit(":",1)[-1].isdigit(): host=host.rsplit(":",1)[0]
            return self.allow_originless_local and host in {"127.0.0.1","localhost"}
        try:
            parsed=urlsplit(raw_origin)
            scheme=parsed.scheme.lower(); hostname=(parsed.hostname or "").lower(); port=parsed.port
        except ValueError:
            return False
        allowed_hosts={self.public_host, f"www.{self.public_host}"}
        if hostname in allowed_hosts and scheme=="https" and port in {None,443}: return True
        return raw_origin.rstrip("/").lower() in {"http://127.0.0.1:9000","http://localhost:9000","http://127.0.0.1","http://localhost"}
    def identify(self,params,browser_session_valid=False):
        token=str(params.get("sessionToken") or params.get("authToken") or "").strip()
        if browser_session_valid:return Identity("USER","browser-session",token_fingerprint(token))
        if self.master_token and token and hmac.compare_digest(token,self.master_token):return Identity("MASTER","master",token_fingerprint(token))
        if self.admin_token and token and hmac.compare_digest(token,self.admin_token):return Identity("ADMIN","admin",token_fingerprint(token))
        if self.auth_token and token and hmac.compare_digest(token,self.auth_token):return Identity("OPERATOR","operator",token_fingerprint(token))
        wid=str(params.get("workerId") or "").strip(); wt=str(params.get("workerToken") or "").strip()
        if wid and wt:return Identity("WORKER",wid,token_fingerprint(wt))
        return Identity("PUBLIC","anonymous",token_fingerprint(token))
    def require(self,method,params,identity):
        if method=="ping" or method in {"AuthenticateMaster","AuthenticateSocialUser"}:return
        if method=="VerifyAdminPasscode":
            configured=os.getenv("SAREMBOK_ADMIN_PASSCODE","").strip(); supplied=str(params.get("passcode") or "").strip()
            if not configured:raise PermissionError("admin_authentication_not_configured")
            if not supplied or not hmac.compare_digest(supplied,configured):raise PermissionError("invalid_admin_credentials")
            return
        required=METHOD_REQUIREMENTS.get(method,"ADMIN")
        if self.level(identity.role)<self.level(required):raise PermissionError("authenticated_session_required" if identity.role=="PUBLIC" else "insufficient_privilege")
        if method=="RegisterWorker":
            enrollment=str(params.get("enrollmentToken") or "").strip()
            if not self.worker_enrollment_token or not enrollment or not hmac.compare_digest(enrollment,self.worker_enrollment_token):raise PermissionError("worker_enrollment_required")
        if method in {"Heartbeat","ClaimTask","CompleteTask","FailTask","ExecuteComputeTask"} and identity.role not in {"WORKER","ADMIN","MASTER","SYSTEM"}:raise PermissionError("worker_authorization_required")
    def log_event(self,logger,event,**fields):logger.info(json.dumps({"event":event,**scrub(fields)},separators=(",",":"),ensure_ascii=False))
    @staticmethod
    def error_payload(code,message,data=None):
        out={"code":code,"message":message}
        if data:out["data"]=scrub(data)
        return out