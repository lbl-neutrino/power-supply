import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
import time
import csv

class Scope():
    def __init__(self, ax, maxt=10, dt=0.1, modules=4):
        self.ax = ax
        self.dt = dt
        self.maxt = maxt
        self.modules = modules
        self.tdata = np.array([])
        self.ydatas = [np.array([]) for _ in range(modules)]  
        self.t0 = time.perf_counter()
        
        self.colors = ['r', 'g', 'm', 'b']
        self.lines = [Line2D([], [], color=self.colors[i], label=f'Module {i+1}') for i in range(modules)]
        #self.lines = [Line2D([], []) for _ in range(modules)]  
        for line in self.lines:
            self.ax.add_line(line)
        self.ax.set_ylim(0, 160)  
        self.ax.set_xlim(0, self.maxt)
        self.ax.set_title("Power of Modules")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Power (W)")
        self.ax.legend(loc='upper left')

    def update(self, data):
        t, powers = data
        self.tdata = np.append(self.tdata, t)
        time_filter = self.tdata > (t - self.maxt)
        self.tdata = self.tdata[time_filter]
        
        for i, power in enumerate(powers):
            self.ydatas[i] = np.append(self.ydatas[i], power)
            self.ydatas[i] = self.ydatas[i][time_filter]
            
        for i, line in enumerate(self.lines):
            line.set_data(self.tdata, self.ydatas[i])
        self.ax.set_xlim(self.tdata[0], self.tdata[0] + self.maxt)
        self.ax.figure.canvas.draw()
        return self.lines

    def emitter(self, filename):
        with open(filename, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)  
            start_time = time.perf_counter()

            while True:
                t = time.perf_counter() - start_time
                try:
                    row = next(csvreader) 
                    powers = [float(row[4 + i*4]) for i in range(self.modules)]  
                    yield t, powers
                except StopIteration:
                    time.sleep(0.1)  
                    continue

if __name__ == '__main__':
    fig, ax = plt.subplots()
    scope = Scope(ax, maxt=20, dt=0.1, modules=4)
    filename = 'module_log.csv'  
    ani = animation.FuncAnimation(fig, scope.update, scope.emitter(filename), interval=100, blit=True)
    plt.show()
