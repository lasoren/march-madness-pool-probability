import pytesseract
from PIL import Image

print(pytesseract.image_to_string(Image.open('bracket_images/luke.png')))
