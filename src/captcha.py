from PIL import Image
from PIL import ImageDraw
from PIL import ImageFilter
from operator import itemgetter

import hashlib,os,math,sys

def magnitude(concordance):
  total = 0
  for word,count in concordance.iteritems():
    total += count ** 2
  return math.sqrt(total)

def getVectorSim(concordance1, concordance2):
  topvalue = 0
  for word, count in concordance1.iteritems():
    if concordance2.has_key(word):
      topvalue += count * concordance2[word]
  sim=topvalue / (magnitude(concordance1) * magnitude(concordance2))
  return sim

def buildvector(im):
  d1 = {}
  count = 0
  for i in im.getdata():
    d1[count] = i
    count += 1
  return d1

class Guesser:

  def __init__(self, iconset_dir,**kw):
    self.iconset_dir=iconset_dir
    self.iconset=self.read_iconset(iconset_dir)
    self.do_print_histogram=0
    self.do_save_debug_images=kw.get("do_save_debug_images", 1)
    
    self.minimal_letter_width=kw.get("minimal_letter_width", 1)
    self.minimal_letter_height=kw.get("minimal_letter_height", 1)
    self.minimal_number_of_set_pixel_per_line=kw.get("minimal_number_of_set_pixel_per_line", 3)
    self.should_be_black=kw.get("should_be_black", lambda pix: pix < 10)
    self.minimal_similarity=kw.get("minimal_similarity",0)

  def guess(self, imagefilename):
    self.imagefilename=imagefilename
    self.orig_image = Image.open(imagefilename).convert("P")
    if self.do_print_histogram:
      self.print_histogram()
      
    self.blackwhite_image = self.convert_to_blackwhite_image()
    if self.do_save_debug_images:
      self.save_debug_image(self.blackwhite_image, "blackandwhite")
    self.letter_bboxes = self.detect_letter_bboxs()
    if not self.letter_bboxes:
      raise Exception("Failed to detect letters in %r"%imagefilename)
    
    if self.do_save_debug_images:
      im=self.blackwhite_image.convert("RGB")
      self.draw_letter_boxes(im, "blue")
      self.save_debug_image(im, "letters")
      
    code = self.find_code(1)
    return code

  def read_iconset(self,iconset_dir):
    imageset = {}

    for letter in os.listdir(iconset_dir):
      subdir=os.path.join(iconset_dir, letter)
      if not os.path.isdir(subdir):
        continue
      temp = []
      for img in os.listdir(subdir):
        image=Image.open(os.path.join(subdir, img)).convert("1")
        temp.append(buildvector(image))
      if temp:
        imageset[letter]=temp
      
    if not imageset:
      raise Exception("No icons at %r"%iconset_dir)

    return imageset
    
  def print_histogram(self):
    his = self.orig_image.histogram()

    values = {}
    for i in range(256):
      values[i] = his[i]

    print "=== top 10 values"
    for j,k in sorted(values.items(), key=itemgetter(1), reverse=True)[:10]:
      print "  value = %3d count=%5d"%(j,k)

  def save_debug_image(self,image,suffix):
    save_next_to_file=0
    if save_next_to_file:
      fn=self.imagefilename
    else:
      fn="___"+os.path.basename(self.imagefilename)
    fn = fn+"-"+suffix+".png"
    image.save(fn)
    
  def convert_to_blackwhite_image(self):
    im = self.orig_image
    im2 = Image.new("P",im.size,255)

    temp = {}
    for x in range(im.size[0]):
      for y in range(im.size[1]):
        pix = im.getpixel((x,y))
        temp[pix] = pix
        if self.should_be_black(pix):
          im2.putpixel((x,y),0)
    return im2

  def detect_letter_bboxs(self):
    def count_pixel_in_column(x):
      res=0
      for y in range(im2.size[1]):
        pix = im2.getpixel((x,y))
        if pix != 255:
          res+=1
      return res

    def count_pixel_in_row(y, start_x, end_x):
      res=0
      for x in range(start_x, end_x):
        pix = im2.getpixel((x,y))
        if pix != 255:
          res+=1
      return res

    def find_non_empty_row(start_x, end_x,ys):
      for y in ys:
        pixel_set = count_pixel_in_row(y,start_x, end_x)
        if pixel_set >= self.minimal_number_of_set_pixel_per_line:
          return y
      return None

    im2 = self.blackwhite_image
    height=im2.size[1]
    inletter = False
    foundletter = False
    start = 0
    end = 0

    letters = []
    for x in range(im2.size[0]):
      setInCol=count_pixel_in_column(x)
      inletter = setInCol>0
      if not foundletter and inletter:
        foundletter = True
        start = x

      if foundletter and not inletter:
        foundletter = False
        end = x
        width = end-start
        if width>=self.minimal_letter_width:
          letters.append((start,end))

    result=[]
    for start_x, end_x in letters:      
      start_y=find_non_empty_row(start_x,end_x, range(height))
      end_y  =find_non_empty_row(start_x,end_x, range(height-1,-1,-1))
      if start_y==None or end_y==None:
        continue
      h=end_y-start_y
      if h>=self.minimal_letter_height:
        result.append((start_x, start_y, end_x,end_y))

    def is_all_black(letter_bbox):
      im3 = im2.crop(letter_bbox)
      return im3.histogram()[0] == im3.size[0]*im3.size[1]
      
    result=[x for x in result if not is_all_black(x)]
    return result
  
  def draw_letter_boxes(self, image, color):
    height=image.size[1]
    draw = ImageDraw.Draw(image)
    for nw_x,nw_y,se_x,se_y in self.letter_bboxes:
      nw=(nw_x,nw_y)
      ne=(se_x,nw_y)
      sw=(nw_x,se_y)
      se=(se_x,se_y)
      draw.line([nw,ne,se,sw,nw], fill=color)
    del draw

  def find_best_single_letter_match(self, letter_bbox):
    im2 = self.blackwhite_image
    im3 = im2.crop(letter_bbox)

    guess = []
    for letter,images in self.iconset.items():
      for imagevector in images:
        sim=getVectorSim(imagevector, buildvector(im3))
        guess.append((sim, letter))

    guess.sort(reverse=True)
    best_sim,best_letter=guess[0]
    return (best_sim,best_letter,im3)

  def find_code(self, write_mismatching_letters):
    res=[]
    
    for letterno in range(len(self.letter_bboxes)):
      bbox=self.letter_bboxes[letterno]
      sim,letter,im=self.find_best_single_letter_match(bbox)
      if sim>=self.minimal_similarity:
        res.append(letter)
      else:
        print "  best guess for letter %d is '%s' with similarity of %.5f which is too low"%(letterno, letter,sim)
        if write_mismatching_letters:
          self.write_unknown_letter_image(im)
        res.append(None)
    if None not in res:
      return "".join(res)
    return res

  def write_unknown_letter_image(self,image):
    md5=hashlib.md5(str(list(image.getdata()))).hexdigest()
    image.save(os.path.join(self.iconset_dir,md5+".png"))
