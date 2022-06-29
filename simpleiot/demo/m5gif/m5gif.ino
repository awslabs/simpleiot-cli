#include <M5Core2.h>
#include <SPI.h>

TFT_eSprite display = TFT_eSprite(&M5.Lcd);

extern const uint8_t frame_0[];
extern const uint8_t *animated_frames[];
extern const size_t animated_frame_size[];
extern const unsigned int animated_frame_count;
extern const unsigned int animated_frame_width;
extern const unsigned int animated_frame_height;

void setup() {
    M5.begin();
    M5.Axp.SetLcdVoltage(3300); // 
    display.createSprite(M5.Lcd.width(), M5.Lcd.height());
    M5.Lcd.clear();
//    display.fillSprite(PURPLE);
//    display.pushSprite(0, 0);

}

void loop() {

  // int frame_size = animated_frame_size[0];
  // M5.Lcd.drawJpg(frame_0, frame_size);

 for (int i=0; i < animated_frame_count; i++) {
   const uint8_t* frame_image = animated_frames[i];
   int frame_size = animated_frame_size[i];
   M5.Lcd.drawJpg(frame_image, frame_size);
   delay(0);
 }

//  display.pushSprite(0, 0);
}
