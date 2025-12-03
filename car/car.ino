#include <Arduino.h>
#include <esp8266wifi.h>
#include <espnow.h>
#include <Ultrasonic.h>
#define in1 D1 // GPIO5
#define in2 D2 // GPIO4
#define in3 D5 // GPIO14
#define in4 D6 // GPIO12
int speed = 80;
int distance = 20;
//--------------------------------------------------
#define trig D7 // GPIO13
#define echo D0 // GPIO16

Ultrasonic ultrasonic(trig, echo);
//--------------------------------------------------
void forward(int);
void drive(int);
struct msg
{
  int car_speed;
  int safe_distance;
} msg_received;

void onDataReceived(uint8_t *mac, uint8_t *data, uint8_t len)
{
  // copy received data to msg_received structure
  memcpy(&msg_received, data, sizeof(msg_received));
  Serial.print("Speed: ");
  Serial.print(msg_received.car_speed);
  Serial.print(" Distance: ");
  Serial.println(msg_received.safe_distance);
  speed = msg_received.car_speed;
  distance = msg_received.safe_distance;
}

void setup()
{

  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);
  pinMode(in3, OUTPUT);
  pinMode(in4, OUTPUT);
  analogWriteRange(255);
  analogWriteFreq(300);
  Serial.begin(9600);
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != 0)
  {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_recv_cb(onDataReceived);
}

void loop()
{
  int dist_now = ultrasonic.read(CM);
  Serial.print("Distance: ");
  Serial.println(dist_now);
  
  drive(dist_now);
}

//-------------------------functions---------------------------

void forward(int speed)
{

  analogWrite(in2, speed+10);
  digitalWrite(in1, LOW);
  analogWrite(in4, speed);
  digitalWrite(in3, LOW);
}

void drive(int dist)
{
  // full speed
  if (dist > distance + 10)
  {
    forward(speed);
  }
  // full speed - 10
  else if (dist < distance + 10 && dist > distance)
  {
    forward(speed - 30);
  }
  // speed = 0 >>>> stop
  else
  {
    forward(0);
  }
}
