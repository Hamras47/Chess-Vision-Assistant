import numpy as np, pytest
from app.vision.grid import split,board_crop
from app.vision.stabilizer import Stabilizer
from app.vision.change_detector import square_difference,AdaptiveThreshold
from app.ui.dpi_coordinates import MonitorCoordinates
from PySide6.QtCore import QRect

def test_grid_splits_64_equal_squares():
    image=np.zeros((160,160,3),dtype=np.uint8); cells=split(image)
    assert len(cells)==64 and all(c.shape==(20,20,3) for c in cells)
def test_changed_square_image_difference():
    a=np.zeros((160,160,3),dtype=np.uint8); b=a.copy(); b[40:60,60:80]=255
    changed=[i for i,(x,y) in enumerate(zip(split(a),split(b))) if np.mean(np.abs(x.astype(int)-y.astype(int)))>9]
    assert changed==[19]
def test_stabilizer_needs_a_change_then_stable_frame():
    s=Stabilizer(delay_ms=0); a=np.zeros((8,8,3),dtype=np.uint8)
    assert not s.observe(a,True); assert not s.observe(a,True); assert s.observe(a,True)
def test_highlight_only_flat_color_change_is_ignored():
    a=np.full((64,64,3),(120,160,190),dtype=np.uint8); b=np.full((64,64,3),(80,180,210),dtype=np.uint8)
    assert square_difference(a,b)<.01
@pytest.mark.parametrize('dpr,expected',[(1.0,(100,100,500,500)),(1.25,(125,125,625,625)),(1.5,(150,150,750,750)),(2.0,(200,200,1000,1000))])
def test_snip_logical_to_physical_at_common_dpi(dpr,expected):
    mapping=MonitorCoordinates(QRect(0,0,1920,1080),{'left':0,'top':0,'width':round(1920*dpr),'height':round(1080*dpr)},dpr)
    r=mapping.selection_to_physical(QRect(100,100,500,500)); assert tuple(r.values())==expected
def test_snip_coordinates_support_monitor_offsets():
    mapping=MonitorCoordinates(QRect(-1536,0,1536,864),{'left':-1920,'top':0,'width':1920,'height':1080},1.25)
    assert mapping.selection_to_physical(QRect(100,50,640,640))=={'left':-1795,'top':62,'width':800,'height':800}
def test_loose_selection_is_normalized_to_square_crop():
    image=np.full((220,240,3),30,dtype=np.uint8)
    for r in range(8):
      for c in range(8): image[20+r*25:20+(r+1)*25,20+c*25:20+(c+1)*25]=210 if (r+c)%2==0 else 80
    crop,bounds=board_crop(image)
    assert crop.shape[0]==crop.shape[1] and 170<=crop.shape[0]<=220
def test_adaptive_threshold_is_bounded():
    threshold=AdaptiveThreshold(); threshold.sample({i:{'combined':.001} for i in range(64)}); assert threshold.value==threshold.minimum
    threshold.sample({i:{'combined':1.0} for i in range(64)}); assert threshold.value==threshold.maximum
