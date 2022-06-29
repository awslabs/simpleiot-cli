import sys
import io
import os

from PIL import Image
from PIL import GifImagePlugin


def gif2jpg(file_name: str, trans_color: tuple):
    """
    convert gif to `num_key_frames` images with jpg format
    :param file_name: gif file name
    :param num_key_frames: result images number
    :param trans_color: set converted transparent color in jpg image
    :return:
    """
    with Image.open(file_name) as im:
        num_key_frames = im.n_frames
        for i in range(num_key_frames):
            im.seek(im.n_frames // num_key_frames * i)
            image = im.convert("RGBA")
            datas = image.getdata()
            newData = []
            for item in datas:
                if item[3] == 0:  # if transparent
                    newData.append(trans_color)  # set transparent color in jpg
                else:
                    newData.append(tuple(item[:3]))
            image = Image.new("RGB", im.size)
            image.getdata()
            image.putdata(newData)
            filename = f"{i}.jpg"
            image.save(filename)


            # gif2jpg("image.gif", (255, 255, 255))  # convert image.gif to jpg images with white background

def write_frame_from_file(outfile, filename, frame_number):
    data_len = os.path.getsize(filename)
    
    with open(filename, 'rb') as infile:
        array_name = f"const unsigned char frame_{frame_number} [{data_len}] = {{" + "\n"
        outfile.write(array_name.encode('utf-8'))
        while True:
            data = infile.read(20)
            if len(data) > 0:
                # outfile.write('\t'.encode('utf-8'))
                for i in range(0, len(data)):
                    d = "0x%02x," % data[i]
                    outfile.write(d.encode('utf-8'))
                outfile.write('\n'.encode('utf-8'))
            else:
                outfile.write('};\n'.encode('utf-8'))
                break
                
    return data_len




def write_frame(outfile, frame, data):
    data_len = len(data)
    array_name = f"const unsigned char frame_{frame} [{data_len}] = {{" + "\n"
    outfile.write(array_name.encode('utf-8'))
    
    start = 0
    skip = 20
    
    count = data_len // skip
    remainder = data_len % skip
    
    for i in range(count):
        buffer = data[start:skip]
        buffer_len = len(buffer)
        for i in range(0, len(buffer)):
            d = "0x%02x," % data[i]
            outfile.write(d.encode('utf-8'))
        outfile.write('\n'.encode('utf-8'))

    if remainder > 0:
        start_remainder = count * skip
        buffer = data[start_remainder:]
        for i in range(0, len(buffer)):
            d = "0x%02x," % data[i]
            outfile.write(d.encode('utf-8'))
        outfile.write('\n'.encode('utf-8'))
        
    outfile.write('};\n\n'.encode('utf-8'))
    

def write_decl(output, frame_count,  image_width, image_height):
    decl_str = f"const unsigned int animated_frame_count = {frame_count};" + "\n"
    output.write(decl_str.encode('utf-8'))
    decl_str = f"const unsigned int animated_frame_width = {image_width};" + "\n"
    output.write(decl_str.encode('utf-8'))
    decl_str = f"const unsigned int animated_frame_height = {image_height};" + "\n"
    output.write(decl_str.encode('utf-8'))
    decl_str = f"const unsigned char* animated_frames[] = {{" + "\n"
    output.write(decl_str.encode('utf-8'))
    for i in range(frame_count):
        decl_str = f"   frame_{i}"
        if i < frame_count-1:
            decl_str += ","
        decl_str += "\n"
        output.write(decl_str.encode('utf-8'))
    decl_str = f"}};" + "\n\n"
    output.write(decl_str.encode('utf-8'))

    
def write_frame_size(output, image_data_size):
    decl_str = f"const unsigned int animated_frame_size[] = {{" + "\n"
    output.write(decl_str.encode('utf-8'))
    for size in image_data_size:
        decl_str = f"  {size}," + "\n"
        output.write(decl_str.encode('utf-8'))
    decl_str = f"}};" + "\n\n"
    output.write(decl_str.encode('utf-8'))
    

def write_header(output):
    decl_str = f"#include <M5Core2.h>" + "\n\n"
    output.write(decl_str.encode('utf-8'))
    

def gif2code(input, output, temp_file):
    with open(output, 'wb') as output:
        with Image.open(input) as im:
            num_key_frames = im.n_frames - 1
            image_width, image_height = im.size
            print(f"Frames: {num_key_frames}")
            frame_sizes = []
            
            for i in range(num_key_frames):
                seek_frame = im.n_frames // num_key_frames * i
                print(f"Getting frame: {seek_frame}")
                im.seek(seek_frame)
                image = im.convert("RGBA")
                datas = image.getdata()
                newData = []
                for item in datas:
                    if item[3] == 0:  # if transparent
                        newData.append(trans_color)  # set transparent color in jpg
                    else:
                        newData.append(tuple(item[:3]))
                image = Image.new("RGB", im.size)
                image.getdata()
                image.putdata(newData)
                image.save(temp_file)
        
#       with Image.open(input) as im:
#           # write_header(output)
#           num_key_frames = im.n_frames
#           image_width, image_height = im.size
#           
#           print(f"Frame: {num_key_frames}")
#           frame_sizes = []
#           
#           for i in range(num_key_frames):
#               im.seek(im.n_frames // num_key_frames * i)
#               image = im.convert("RGBA")
#               image_data = image.getdata()
#               new_data = []
#               for item in image_data:
#                   if item[3] == 0:  # see if transparent
#                       new_data.append(trans_color)
#                   else:
#                       new_data.append(tuple(item[:3]))
#               new_image = Image.new("RGB", im.size)
#               new_image.getdata()
#               new_image.putdata(new_data)
#               image.save(temp_file)

                frame_size = write_frame_from_file(output, temp_file, i)
                frame_sizes.append(frame_size)
                os.remove(temp_file)
                
#               with io.BytesIO() as memfile:
#                   new_image.save(memfile, "JPEG")
#                   frame_data = memfile.getvalue()
#                   frame_size = len(frame_data)
#                   write_frame(output, i, frame_data)
#                   frame_sizes.append(frame_size)

            write_frame_size(output, frame_sizes)
            write_decl(output, num_key_frames, image_width, image_height)
            

if __name__ == "__main__":
    source = "image.gif"
    output = "animation.c"
    temp_file = "_image_temp.jpg"
    
    if (len(sys.argv) > 1):
        source = sys.argv[1]
        if (len(sys.argv) > 2):
            output = sys.argv[2]

    gif2code(source, output, temp_file)
    print("Done!")

#   else:
#       print("Usage: gif2code [source animated gif file] [output C file]")
    