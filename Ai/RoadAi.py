import sounddevice as sd
import numpy as np
import tensorflow as tf
import time
import threading
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk

MODEL_PATH = "model.tflite"
LABELS_PATH = "labels.txt"

# ================================
#      Load Model & Labels
# ================================
with open(LABELS_PATH, "r") as f:
    labels = [line.strip() for line in f.readlines()]

interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

REQUIRED_SAMPLES = input_details[0]['shape'][1]
SAMPLE_RATE = 44100

audio_buffer = np.array([], dtype=np.float32)

CONF_THRESHOLD = 0.90
REQUIRED_REPEATS = 2
history = []

current_label = ""  
ser = None          


# ================================
#     Tkinter GUI
# ================================
class App:
    def __init__(self, root):
        self.root = root
        root.title("Voice Detector")

    
        self.canvas = tk.Canvas(root, width=220, height=220)
        self.canvas.grid(row=0, column=0, padx=10, pady=10)
        self.circle = self.canvas.create_oval(10, 10, 210, 210, fill="lightgray")
        self.text = self.canvas.create_text(110, 110, text="...", font=("Arial", 14, "bold"))

       
        ttk.Label(root, text="Serial Port:").grid(row=1, column=0, sticky="w")
        self.combo = ttk.Combobox(root, width=25, state="readonly")
        self.combo.grid(row=2, column=0, padx=10, pady=5)
        self.combo.bind("<Button-1>", lambda e: self.refresh_ports())
        self.refresh_ports()
        self.combo = ttk.Combobox(root, width=25, state="readonly")
        self.combo.grid(row=2, column=0, padx=10, pady=5)

      
        self.combo.bind("<Button-1>", lambda e: self.refresh_ports())

       
        self.connect_btn = ttk.Button(root, text="Connect", command=self.connect_serial)
        self.connect_btn.grid(row=3, column=0, pady=5)

    
        self.status = ttk.Label(root, text="Not connected", foreground="red")
        self.status.grid(row=4, column=0, pady=5)

    
        self.update_ui()

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.combo["values"] = ports
        if ports:
            self.combo.current(0)

    def connect_serial(self):
        global ser
        port = self.combo.get()
        if not port:
            self.status.config(text="No port selected", foreground="red")
            return

        try:
            ser = serial.Serial(port, 9600, timeout=1)
            self.status.config(text=f"Connected: {port}", foreground="green")
            ser.write(b'{"detict":"background","connect":"yes"}\n')
        except:
            ser = None
            self.status.config(text="Connection failed", foreground="red")

    def update_ui(self):
        global current_label

        if current_label:
            self.canvas.itemconfig(self.circle, fill="lightgreen")
            self.canvas.itemconfig(self.text, text=current_label)
        else:
            self.canvas.itemconfig(self.circle, fill="lightgray")
            self.canvas.itemconfig(self.text, text="...")

        self.root.after(150, self.update_ui)


# ================================
#      using ai model
# ================================
def classify_audio(audio):
    audio = audio.astype(np.float32)
    audio = audio / np.max(np.abs(audio))
    audio = audio.reshape(1, REQUIRED_SAMPLES)

    interpreter.set_tensor(input_details[0]["index"], audio)
    interpreter.invoke()

    output = interpreter.get_tensor(output_details[0]["index"])[0]
    idx = np.argmax(output)

    return labels[idx], float(output[idx])


def audio_callback(indata, frames, time_, status):
    global audio_buffer, history, current_label, ser

    audio_buffer = np.concatenate([audio_buffer, indata[:, 0]])

    if len(audio_buffer) >= REQUIRED_SAMPLES:
        chunk = audio_buffer[:REQUIRED_SAMPLES]
        audio_buffer = audio_buffer[REQUIRED_SAMPLES:]

        label, conf = classify_audio(chunk)

        if conf < CONF_THRESHOLD:
            return

        history.append(label)
        if len(history) > REQUIRED_REPEATS:
            history.pop(0)

        if len(history) == REQUIRED_REPEATS and all(h == label for h in history):
            print(f"FINAL DETECTED: {label} ({conf*100:.1f}%)")
            current_label = label

            if ser:
                try:
                    msg = f'{{"detict":"{label}","connect":"yes"}}\n'
                    ser.write(msg.encode())
                except:
                    pass


def audio_thread():
    with sd.InputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        callback=audio_callback,
        blocksize=2048
    ):
        while True:
            time.sleep(0.1)


# ================================
#            Main
# ================================
root = tk.Tk()
app = App(root)

t = threading.Thread(target=audio_thread, daemon=True)
t.start()

root.mainloop()
