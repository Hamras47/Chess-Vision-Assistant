import os, json, base64, time, logging
from dotenv import load_dotenv
load_dotenv()
DEFAULT_OPENAI_VISION_MODEL = 'gpt-5.6-luna'
class AIError(RuntimeError): pass
def normalize_model(model):
 """Return the configured API model verbatim, with only an empty value defaulted."""
 return str(model or '').strip() or DEFAULT_OPENAI_VISION_MODEL

def resolve_model(settings_model=None, environment=None):
 """Settings take precedence over .env, then use the V1.6 Luna default."""
 env = os.environ if environment is None else environment
 return normalize_model(settings_model or env.get('OPENAI_VISION_MODEL') or DEFAULT_OPENAI_VISION_MODEL)
class OpenAIClient:
 def __init__(self, model=None, client=None):
  self.model=normalize_model(model or os.getenv('OPENAI_VISION_MODEL') or DEFAULT_OPENAI_VISION_MODEL); self._client=client
 def ready(self): return bool(os.getenv('OPENAI_API_KEY'))
 def client(self):
  if not self.ready(): raise AIError('OpenAI API key missing. Add OPENAI_API_KEY to .env and restart.')
  if self._client is None:
   try:
    from openai import OpenAI; self._client=OpenAI(timeout=20,max_retries=2)
   except Exception as e: raise AIError(f'OpenAI SDK unavailable: {e}')
  return self._client
 def recognize(self,png,schema,prompt):
  started=time.monotonic(); data='data:image/png;base64,'+base64.b64encode(png).decode()
  logging.info('OPENAI_REQUEST_STARTED model=%s png_bytes=%d',self.model,len(png))
  try:
   r=self.client().responses.create(model=self.model,store=False,input=[{'role':'system','content':prompt},{'role':'user','content':[{'type':'input_text','text':'Transcribe this board.'},{'type':'input_image','image_url':data,'detail':'high'}]}],text={'format':{'type':'json_schema','name':'board_recognition','strict':True,'schema':schema}})
   latency=time.monotonic()-started; logging.info('OPENAI_REQUEST_SUCCEEDED model=%s response_status=%s request_id=%s latency_seconds=%.3f',self.model,getattr(r,'status','unknown'),getattr(r,'_request_id','unknown'),latency)
   return json.loads(r.output_text),latency,{'api_success':True,'status':getattr(r,'status','unknown'),'request_id':getattr(r,'_request_id','unknown'),'model':self.model}
  except AIError: raise
  except Exception as e:
   logging.exception('OPENAI_REQUEST_FAILED model=%s exception_type=%s message=%s http_status=%s request_id=%s',self.model,type(e).__name__,str(e),getattr(e,'status_code','unknown'),getattr(e,'request_id','unknown'))
   raise AIError(f'OpenAI request failed: {type(e).__name__}: {e}')
