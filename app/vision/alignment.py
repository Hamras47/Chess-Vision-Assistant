"""Small, image-only board geometry helpers used before chess move inference."""
from .grid import board_crop

def plausible_board_crop(image):
    if image is None or image.ndim != 3:return False,'missing image'
    height,width=image.shape[:2]
    if min(width,height)<64:return False,'board is too small'
    if abs(width-height)>2:return False,'board crop is not square'
    return True,'ok'

def corrected_board(image,origin):
    """Fit a square board inside an anchor image and return its desktop rectangle."""
    crop,(x,y,width,height)=board_crop(image)
    valid,reason=plausible_board_crop(crop)
    if not valid:return None,None,reason
    rect={'left':origin['left']+x,'top':origin['top']+y,'width':width,'height':height}
    return crop,rect,'ok'

def search_region(region,margin=None):
    margin=max(30,int(max(region['width'],region['height'])*.15)) if margin is None else margin
    return {'left':max(0,region['left']-margin),'top':max(0,region['top']-margin),'width':region['width']+2*margin,'height':region['height']+2*margin}

def geometry_changed(old_rect,new_rect):
    return old_rect is None or any(old_rect.get(key)!=new_rect.get(key) for key in ('left','top','width','height'))
