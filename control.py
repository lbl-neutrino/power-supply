import tkinter as tk
from power_supply import power_supply, addr, mods
import json



class StateManager:


    def __init__(self, modules, statefile='.current_state.json'):
            
        self.voltage_read_format = 'MOD{}_VOLTAGE'
        
        self.enabled_read_format = 'MOD{}_ENABLED'
        self.modules=modules
        self.statefile=statefile
        self.state=self.get_default_state()
        
        try:
            with open(self.statefile, 'r') as f:
                self.state = json.load(f)
        except:
            print('No known system state, starting with defaults!')


    def set_voltage(self, i, val):
        self.state[ self.voltage_read_format.format(self.modules[i]) ] = val
        self.write_state()

    def set_enabled(self, i, val):
        self.state[ self.enabled_read_format.format(self.modules[i]) ] = val
        self.write_state()

    def get_voltage(self, i):
        return self.state[ self.voltage_read_format.format(self.modules[i]) ]

    def get_enabled(self, i):
        return self.state[ self.enabled_read_format.format(self.modules[i]) ]

    def get_default_state(self):
        d={}
        for indx in self.modules: 
            d[self.voltage_read_format.format(indx)] = 0
            d[self.enabled_read_format.format(indx)] = False
        return d

    def write_state(self):
        with open(self.statefile, 'w') as f:
            json.dump(self.state, f, indent=4)

    def update(self):
        with open(self.statefile, 'r') as f:
            self.state = json.load(f)

class Application(tk.Frame):

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
    
        self.page = mods
        self.state = StateManager(self.page)
        self.inputs = {}
        self.create_widgets()
        self.supply = power_supply(addr)

    def create_widgets(self):
        for i in range(3):
            frame = tk.Frame(self)
            frame.pack(side="top")

            label = tk.Label(frame, text=f"HEATER {i+1}:")
            label.pack(side="left")

            entry = tk.Entry(frame)
            entry.pack(side="left")

            update_button = tk.Button(frame, text="Update", command=lambda i=i: self.update_value(i))
            update_button.pack(side="left")
            
            self.inputs[f"input_{i+1}"] = {"entry": entry, "enabled": False}
            
            text = {

                    1 : 'ON',
                    0 : 'OFF'

                }

            enabled_button = tk.Button(frame, text=text[int(self.state.get_enabled(i))], command=lambda i=i: self.toggle_enabled(i))
            enabled_button.pack(side="left")
            self.inputs[f"input_{i+1}"]["enabled_button"] = enabled_button
            
            voltage_label = tk.Label(frame, text="Set Voltage:")
            voltage_label.pack(side="left")

            value_label = tk.Label(frame, text=self.state.get_voltage(i))
            value_label.pack(side="left")
            self.inputs[f"input_{i+1}"]["value_label"] = value_label

        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.pack(side="bottom")

        self.all_off = tk.Button(self, text="ALL OFF", fg="red",
                              command=self.all_off)
        self.all_off.pack(side="bottom")

    def all_off(self):
        for i in range(len(self.page)):
            self.state.set_enabled(i, False)
            self.toggle_enabled_off(i)

    def turn_on(self, i):
        #Set the desired voltage before enabling module
        self.state.update() 
        voltage = self.state.get_voltage(i)

        #enable supply
        self.set_voltage(i, voltage)
        self.supply.on_mod( self.page[i] ) 

    def turn_off(self, i):
        self.supply.set_voltage( self.page[i], 0 ) #Turn supply to 0 to avoid accidental power up
        self.supply.off_mod( self.page[i] ) #Turn off enable bit for supply

    def set_voltage(self, i, voltage):
        self.supply.set_voltage( self.page[i], voltage )

    def toggle_enabled_off(self, i):
        self.inputs[f"input_{i+1}"]["enabled"] = False
        self.inputs[f"input_{i+1}"]["enabled_button"].config(text="OFF")
        
        self.state.set_enabled(i, False)
        self.turn_off(i)

    def toggle_enabled(self, i):
        #Switch state: if ON, turn OFF.
        self.inputs[f"input_{i+1}"]["enabled"] = not self.inputs[f"input_{i+1}"]["enabled"] 
        self.state.set_enabled(i, self.inputs[f"input_{i+1}"]["enabled"])
        if self.inputs[f"input_{i+1}"]["enabled"]:
            self.inputs[f"input_{i+1}"]["enabled_button"].config(text="ON")
            self.turn_on(i)
        else:
            self.inputs[f"input_{i+1}"]["enabled_button"].config(text="OFF")
            self.turn_off(i)

    def update_value(self, i):
        try:
            value = float(self.inputs[f"input_{i+1}"]["entry"].get())
            self.state.set_voltage(i, value)
            self.inputs[f"input_{i+1}"]["value_label"].config(text=f"{value:.2f}")
            self.set_voltage(i, value)
        except ValueError:
            self.inputs[f"input_{i+1}"]["value_label"].config(text="Invalid input")

root = tk.Tk()
root.title('POWER SUPPLY CONTROLLER')
app = Application(master=root)
app.mainloop()

