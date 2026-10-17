 
//Librares for the temperature(dht),
#include <Filters.h>                     
#include <DHT.h>;
#include <Adafruit_Sensor.h>

//Constants  for current sensor
#define ACS_Pin A0                        //Sensor data pin on A0 analog input
//Constants  for temprature(DHT22)
#define DHTPIN 7           // what pin we're connected to
#define DHTTYPE DHT22      // DHT 22  (AM2302)
DHT dht(DHTPIN, DHTTYPE);  // Initialize DHT sensor for normal 16mhz Arduino


//Variables dcclare
float temp; //Stores temperature value
float ACS_Value;                              //Here we keep the raw data valuess of current sensor
float testFrequency = 50;                    // test signal frequency (Hz)
float windowLength =1.0/testFrequency;     // how long to average the signal, for statistist
int xpin = A3;       //adxl x pin value         
 int ypin = A2;      //adxl y pin value             
 int zpin = A1;       //adxl z pin value   
 float zg;

unsigned long printPeriod = 1; // in milliseconds Track time in milliseconds since last reading 
unsigned long previousMillis = 0;

void setup() {
  Serial.begin(57600);    // Start the serial port
  pinMode(ACS_Pin,INPUT);  //Define the pin mode
  pinMode(xpin,INPUT);  //Define the pin mode
  pinMode(ypin,INPUT);  //Define the pin mode
  pinMode(zpin,INPUT);  //Define the pin mode  
  dht.begin();
  delay(10);
}

void loop() {
  current_function();
  Serial.println("Current Value Taken");
//  vibration_value();
  //Serial.println("Vibration Value Taken");
  temp_fun();
  Serial.println("Temperature Value Taken");

}

float current_function(){
  RunningStatistics inputStats;                 // create statistics to look at the raw test signal
  inputStats.setWindowSecs( windowLength );     //Set the window length
    int i=0;
  while( i<30000 ) {   
    ACS_Value = analogRead(ACS_Pin);  // read the analog in value:
    inputStats.input(ACS_Value);  // log to Stats function
        
    if((unsigned long)(millis() - previousMillis) >= printPeriod) { //every second we do the calculation
      previousMillis = millis();   // update time
  
      Serial.println( ACS_Value );

    }
  
    i=i+1;
    delayMicroseconds(2);
  }
  return ACS_Value;
}
/*float vibration_value()
{
  float testFrequency1 = 550;                    // test signal frequency (Hz)
  float windowLength1 =0.550/testFrequency;     // how long to average the signal, for statistist
  unsigned long printPeriod1 = 0.1; // in milliseconds Track time in milliseconds since last reading 
  float zero_G_x = 492.3;
  float zero_G_y = 488.55;
  float zero_G_z = 507.6;

  float scale_x = 99.2;
  float scale_y = 100.25;
  float scale_z = 97.7;
  unsigned long previousMillis1 = 0;
   RunningStatistics inputStats;                 // create statistics to look at the raw test signal
  inputStats.setWindowSecs( windowLength1 );     //Set the window length
     int i=0;
  while( i<30000 ) { 
  float x = analogRead(xpin);                             //reads values from x-pin & measures acceleration in X direction 
 
  float xg =(x - zero_G_x)/scale_x  ;                       //converts the mapped value into acceleration in terms of "g"
  inputStats.input(xg);  // log to Stats function                                 
   
 float y = analogRead(ypin);

  float yg = (y - zero_G_y)/scale_y;
   inputStats.input(yg);  // log to Stats function 
 
   float z = analogRead(zpin);
 
  float zg =(z - zero_G_z)/scale_z;
  inputStats.input(zg);  // log to Stats function 
   if((unsigned long)(micros() - previousMillis1) >= printPeriod1) { //every second we do the calculation
      previousMillis1 = micros();   // update time 
  Serial.print(xg);
  Serial.print("\t"); 
  
  Serial.print(yg);
  Serial.print("\t");

  Serial.print(zg);
  Serial.println("\t"); 
   }
   
     i=i+1;
     delayMicroseconds(2);
     }
     return zg;
}
*/

float temp_fun()
{
   RunningStatistics inputStats;                 // create statistics to look at the raw test signal
  inputStats.setWindowSecs( windowLength );     //Set the window length   
  unsigned long previousMillis = 0;
   int i=0;
  while( i<100000 ) {   
    //Read data and store it to variables hum and temp
    temp= dht.readTemperature();
 
    inputStats.input(temp);  // log to Stats function       
    if((unsigned long)(millis() - previousMillis) >= printPeriod) {
      //every second we do the calculation
      previousMillis = millis();   // update time 
    //Print temp values to serial monitor
    Serial.println(temp);
   
  
  }
    i=i+1;
    delayMicroseconds(2);
}
return temp;
}
