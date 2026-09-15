import os, json, base64, time, logging
from dotenv import load_dotenv
from app.core.credentials import CredentialStore, resolve_openai_key
load_dotenv()
DEFAULT_OPENAI_VISION_MODEL = 'gpt-5.6-terra'
# Verified against the official OpenAI model catalog, September 2026.
VISION_MODELS = {'gpt-5.6-terra': 'GPT-5.6 Terra', 'gpt-5.6-luna': 'GPT-5.6 Luna'}
class AIError(RuntimeError): pass
def normalize_model(model):
 """Return the configured API model verbatim, with only an empty value defaulted."""
 return str(model or '').strip() or DEFAULT_OPENAI_VISION_MODEL

def resolve_model(settings_model=None, environment=None):
 """Supported saved choice, developer environment override, then Terra.

 An invalid saved value is ignored; environment overrides remain explicit API IDs.
 """
 env = os.environ if environment is None else environment
 saved = str(settings_model or '').strip()
 return saved if saved in VISION_MODELS else normalize_model(env.get('OPENAI_VISION_MODEL'))
class OpenAIClient:
 def __init__(self, model=None, client=None, credential_store=None, api_key=None):
  self.model=normalize_model(model or os.getenv('OPENAI_VISION_MODEL') or DEFAULT_OPENAI_VISION_MODEL); self._client=client; self.credential_store=credential_store or CredentialStore(); self._explicit_api_key=api_key
 def resolved_key(self):
  if self._explicit_api_key is not None: return self._explicit_api_key.strip(), 'explicit'
  return resolve_openai_key(self.credential_store)
 def ready(self): return bool(self.resolved_key()[0])
 def client(self):
  api_key,_=self.resolved_key()
  if not api_key: raise AIError('OpenAI API key required. Add your API key in Settings to use board scanning.')
  if self._client is None:
   try:
    from openai import OpenAI; self._client=OpenAI(api_key=api_key,timeout=20,max_retries=0)
   except Exception as e: raise AIError(f'OpenAI SDK unavailable ({type(e).__name__})') from None
  return self._client
 def test_connection(self):
  """Validate authentication with a metadata request that consumes no model tokens."""
  try:
   self.client().models.list()
  except Exception as e:
   name=type(e).__name__
   if name in ('AuthenticationError','PermissionDeniedError'): raise AIError('Invalid API key')
   if name in ('APITimeoutError','TimeoutError'): raise AIError('Request timed out')
   if name in ('APIConnectionError','ConnectionError'): raise AIError('Network unavailable')
   raise AIError(f'API error ({name})')
  return True
 def recognize(self,png,schema,prompt):
  started=time.monotonic(); data='data:image/png;base64,'+base64.b64encode(png).decode()
  logging.info('OPENAI_REQUEST_STARTED model=%s png_bytes=%d',self.model,len(png))
  try:
   r=self.client().responses.create(model=self.model,store=False,input=[{'role':'system','content':prompt},{'role':'user','content':[{'type':'input_text','text':'Transcribe this board.'},{'type':'input_image','image_url':data,'detail':'high'}]}],text={'format':{'type':'json_schema','name':'board_recognition','strict':True,'schema':schema}})
   latency=time.monotonic()-started; logging.info('OPENAI_REQUEST_SUCCEEDED model=%s response_status=%s request_id=%s latency_seconds=%.3f',self.model,getattr(r,'status','unknown'),getattr(r,'_request_id','unknown'),latency)
   return json.loads(r.output_text),latency,{'api_success':True,'status':getattr(r,'status','unknown'),'request_id':getattr(r,'_request_id','unknown'),'model':self.model}
  except AIError: raise
  except Exception as e:
   safe = AIError(f'OpenAI request failed ({type(e).__name__}). Check your connection and API settings.')
   logging.error('OPENAI_REQUEST_FAILED model=%s exception_type=%s',self.model,type(e).__name__,exc_info=(AIError,safe,e.__traceback__))
   raise safe from None
