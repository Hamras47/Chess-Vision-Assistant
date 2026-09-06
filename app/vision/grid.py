def locked_square_crop(image):
    """Center-crop a user's selection to a square without expanding it."""
    height,width=image.shape[:2]; size=min(width,height); x=(width-size)//2; y=(height-size)//2
    return image[y:y+size,x:x+size],(x,y,size,size)
