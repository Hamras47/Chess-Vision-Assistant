import os, json, base64, time, logging
from dotenv import load_dotenv
load_dotenv()
class AIError(RuntimeError): pass
def normalize_model(model):
 # Codex desktop model aliases are not interchangeable with OpenAI API model IDs.
 if model in {'gpt-5.6-luna','gpt-5.6-terra','gpt-5.6-sol'}: return 'gpt-5.2'
 return model
class OpenAIClient:
 def __init__(self, model=None, client=None):
  requested=model or os.getenv('OPENAI_VISION_MODEL','gpt-5.2'); self.model=normalize_model(requested); self._client=client
  if requested!=self.model: logging.warning('Configured model %s is a Codex alias, using API vision model %s',requested,self.model)
 def ready(self): return bool(os.getenv('OPENAI_API_KEY'))
 def client(self):
  if not self.ready(): raise AIError('OpenAI API key missing. Add OPENAI_API_KEY to .env and restart.')
  if self._client is None:
   try:
    from openai import OpenAI; self._client=OpenAI(timeout=30,max_retries=2)
   except Exception as e: raise AIError(f'OpenAI SDK unavailable: {e}')
  return self._client
 def recognize(self,png,schema,prompt):
  started=time.monotonic(); data='data:image/png;base64,'+base64.b64encode(png).decode()
  logging.info('AI request start model=%s png_bytes=%d',self.model,len(png))
  try:
   r=self.client().responses.create(model=self.model,store=False,input=[{'role':'system','content':prompt},{'role':'user','content':[{'type':'input_text','text':'Transcribe this board.'},{'type':'input_image','image_url':data,'detail':'high'}]}],text={'format':{'type':'json_schema','name':'board_recognition','strict':True,'schema':schema}})
   latency=time.monotonic()-started; logging.info('AI request succeeded=yes model=%s response_status=%s request_id=%s latency=%.3fs',self.model,getattr(r,'status','unknown'),getattr(r,'_request_id','unknown'),latency)
   return json.loads(r.output_text),latency,{'api_success':True,'status':getattr(r,'status','unknown'),'request_id':getattr(r,'_request_id','unknown'),'model':self.model}
  except AIError: raise
  except Exception as e:
   logging.exception('AI request succeeded=no model=%s error_type=%s http_status=%s request_id=%s',self.model,type(e).__name__,getattr(e,'status_code','unknown'),getattr(e,'request_id','unknown'))
   raise AIError(f'OpenAI request failed: {type(e).__name__}: {e}')
