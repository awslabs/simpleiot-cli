# gif2code

This is a tool that will convert an animated GIF into C code that can be embedded inside an
Arduino program running on an M5Core2 device.

The player can easily be ported to other displays. 

To run, create a Python 3.8+ virtualenv, then use pip to install the requirements.txt
libraries:

% python venv -m venv
% source venv/bin/activate
% pip install -r requirements.txt

To run the code:

% python gif2code.py [input-gif] [output-C]

It uses PIL (Pillow) to convert each frame into a JPEG file, then converts each JPEG frame
into a C structure. The output contains each frame, an array with all the frames, 
number of frames, and the dimension of the animation.

The m5gif.ino file contains the code that loads each frame and plays them back. Since it's
bit-banging each frame, the frame rate isn't going to be spectacular.

A much better solution is to port Lottie (which is included with lvgl) to run natively, but
this works off popular .GIF formats so you can use any gif converter you want.

Note that it assumes the GIF file is 320 x 240. If it's smaller, you can use the sprite feature
in M5.Lcd library to write to only a portion of the screen. That will likely have better
performance than writing to the whole screen.

