#!/usr/bin/env python3

import serial, time, threading, json
from flask import Flask, jsonify

SERIAL_PORT = 'COM3'
BAUD_RATE = 38400
TIMEOUT = 1.0  # seconds between SOH and EOT

latest_data = {
    "m1_msg_counter": 0,
    "m2_msg_counter": 0,
    "m3_msg_counter": 0
}

def pretty_print_aligned(json_obj):
    # Convert to dict if it's a JSON string
    #if isinstance(json_obj, str):
    #    json_obj = json.loads(json_obj)
    #else:
    #    return "{}"

    if len(json_obj.keys() ) == 0 :
        return "{\n\n}"
    
    # Find the longest key for padding
    max_key_len = max(len(str(key)) for key in json_obj.keys())

    # Build formatted lines
    lines = []
    for key, value in json_obj.items():
        padded_key = str(key).ljust(max_key_len)
        formatted_value = json.dumps(value, ensure_ascii=False)
        lines.append(f"{padded_key} : {formatted_value}")

    # Print result
    json_str = "{\n"
    for line in lines:
        json_str = json_str + f"  {line}\n"
    json_str = json_str + "}\n"
    return json_str




def parse_message(msg_bytes):
    print()
    print()
    try:
        if msg_bytes[1] == 0x14 and len(msg_bytes) == 11 and chr(msg_bytes[2]) == "R" and msg_bytes[4] == "G" and msg_bytes[6] == "W" and msg_bytes[8] == "w":
                                  # Message 1:  DC4 - always first message in sequence
                                  #   0    1  2 3 4 5 6 7 8 9   
                                  # [SOH][DC4]R«x»G«x»W«x»w«x»[EOT]
            m1_lights_raw_str = msg_bytes[2:10]
            latest_data["m1_lights"] = '>>>' + m1_lights_raw_str.decode('utf-8')  + '<<<'
            latest_data["m1_msg_counter"] = latest_data["m1_msg_counter"] + 1
            
        elif msg_bytes[1] == 0x13:  # DC3
            if len(msg_bytes) == 13 and chr(msg_bytes[2]) in "RNJB" and msg_bytes[3] == 0x2 and chr(msg_bytes[6]) == ":" and chr(msg_bytes[9]) in " ." :
                                    # Message 2:  Match Time Info & Status
                                    #   0    1  2  3   456789ab   12
                                    # [SOH][DC3]Z[STX]«MM:SS.DC»[EOT]
                time_type = {'R': 'Running Time', 'N': 'Net Time (Time Stopped)', 'J': 'Injury Time', 'B': 'Break Time'}
                m2_timer_raw_str = msg_bytes[4:12]
                latest_data["m2_timer_status"] = chr(msg_bytes[2])
                latest_data["m2_timer_mmssdc"] = '>>>' + m2_timer_raw_str.decode('utf-8')  + '<<<'
                latest_data["m2_msg_counter"] = latest_data["m2_msg_counter"] + 1
                
            elif len(msg_bytes) == 29 and msg_bytes[2] == 0x44 and msg_bytes[3] == 0x2 and chr(msg_bytes[6]) == ":" and msg_bytes[9] == 0x2 and msg_bytes[15] == 0x2 and msg_bytes[21] == 0x2  and msg_bytes[23] == 0x2  and msg_bytes[25] == 0x2 :
                                    # Message 3: Competitors Data
                                    #   0    1  2  3  45678  9  abc   15 16 --20 21 22 23 24 25
                                    # [SOH][DC3]D[STX]XX:YY[STX]AABBb[STX]CCDDd[STX]P[STX]R[STX]vW[EOT]
                m3_score_raw_str = msg_bytes[4:9]
                latest_data["m3_score"] = '>>>' + m3_score_raw_str.decode('utf-8')  + '<<<'
                                
                m3_YRB_right_raw_str = msg_bytes[10:15]
                m3_YRB_left_raw_str  = msg_bytes[16:21]
                latest_data["m3_YRB_right"] = '>>>' + m3_YRB_right_raw_str.decode('utf-8')  + '<<<'
                latest_data["m3_YRB_left"]  = '>>>' + m3_YRB_left_raw_str.decode('utf-8')  + '<<<'
                
                m3_priority = chr(msg_bytes[22])
                m3_period = chr(msg_bytes[24]) # if period == 0 then tablo OFF
                latest_data["m3_priority"] = m3_priority
                latest_data["m3_period"] = m3_period
                
                m3_video_requests = msg_bytes[26:28]
                latest_data["m3_video_requests"] = '>>>' + m3_video_requests.decode('utf-8')  + '<<<'
                latest_data["m3_msg_counter"] = latest_data["m3_msg_counter"] + 1
                
            elif len(msg_bytes) == 12 and msg_bytes[2] == 0x49 and msg_bytes[3] == 0x2 and msg_bytes[5] == 0x2 and msg_bytes[7] == 0x2 and msg_bytes[9] == 0x2 :
                                     # Message 4: Status Info from Fencing Piste Apparatus
                                     #   0    1  2  3  4  5  6  7  8  9  a  b  c  d  
                                     # [SOH][DC3]I[STX]M[STX]W[STX]S[STX]N[STX]?[EOT]  # ????? [STX]VW
                m4_raw_str =  chr(msg_bytes[4]) + chr(msg_bytes[6]) +chr(msg_bytes[8]) +chr(msg_bytes[10])
                latest_data["m4_raw_str"] = m4_raw_str
            
            else:
                for i in range(len(msg_bytes)):
                    if msg_bytes[i] < 32:
                        msg_bytes[i] = ord('_') 
                print()
                print("unknown message format (" + str(len(msg_bytes)) + " bytes length):" )
                print(msg_bytes.decode('ascii'))
                print()


            
    except Exception as e:
        print(f"Parse error: {e}")

def read_serial():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    buffer = bytearray()
    in_message = False
    start_time = None

    while True:
        byte = ser.read(1)
        if not byte:
            continue

        b = byte[0]
        if b == 0x01:  # SOH
            buffer = bytearray([b])
            in_message = True
            start_time = time.time()
        elif in_message:
            buffer.append(b)
            if b == 0x04:  # EOT
                parse_message(buffer)
                print(' ')
                print(' ')
                print(' ')
                #print(json.dumps(latest_data, indent=4))
                s = pretty_print_aligned(latest_data)
                print(s)
                with open("data_log.txt", "a") as f:
                    f.write(s + "\n\n\n")  # Add newline for readability

                in_message = False
            elif time.time() - start_time > TIMEOUT:
                buffer.clear()
                in_message = False

# Start serial thread
threading.Thread(target=read_serial, daemon=True).start()

# HTTP server
app = Flask(__name__)

@app.route('/data.json')
def serve_json():
    return jsonify(latest_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)