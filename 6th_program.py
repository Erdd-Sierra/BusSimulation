#これをみせる
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QLineEdit, QTextEdit
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class BusSimulation:
    def __init__(self, n, initial_arrival_offsets):
        self.n = n
        self.initial_arrival_offsets = initial_arrival_offsets
        self.max_students = 900
        self.bus_capacity = 60
        self.simulation_time = 6600
        self.t = 0
        self.i = 0
        self.q = []
        self.b = [0 for _ in range(n)]
        self.b_station_arrive = [offset for offset in initial_arrival_offsets]
        self.b_station_leave = [[] for _ in range(n)]
        self.b_school_arrive = [[] for _ in range(n)]
        self.b_school_leave = [[] for _ in range(n)]
        self.b_station_return = [[] for _ in range(n)]
        self.b_wait_start = [0 for _ in range(n)]
        self.x = self.generate_arrival_times()
        self.queue_lengths = []
        self.bus_logs = [[] for _ in range(n)]
        self.boarding_log = []
        self.student_log = []
        self.late_students = []

    def generate_arrival_times(self):
        arrival_times = []
        t = 0
        student_id = 0
        while len(arrival_times) < self.max_students:
            if 0 <= t < 2400:
                interval = 48
            elif 2400 <= t < 4200:
                interval = 2
            elif 4200 <= t < 4800:
                interval = 4
            elif 4800 <= t < 6600:
                interval = 12
            else:
                break
            t += interval
            arrival_times.append((student_id, t))
            student_id += 1
        return arrival_times[:self.max_students]

    def step(self):
        while self.i < len(self.x) and self.x[self.i][1] == self.t:
            self.q.append(self.x[self.i])
            self.i += 1

        for j in range(self.n):
            if self.t >= self.b_station_arrive[j]:
                if self.b[j] == 0:
                    self.b_wait_start[j] = self.t

                boarded_students = []
                while self.b[j] < self.bus_capacity and self.q:
                    student = self.q.pop(0)
                    self.b[j] += 1
                    boarded_students.append(student[0])
                    self.student_log.append((student[0], j, self.t, 'board'))

                if boarded_students:
                    self.boarding_log.append((self.t, j, self.b[j], boarded_students))

                if self.b[j] == self.bus_capacity or not self.q or (self.t - self.b_wait_start[j] >= 360):
                    depart = self.t
                    school_arr = self.t + 900
                    school_dep = self.t + 1200
                    return_arr = self.t + 2100

                    self.b_station_leave[j].append(depart)
                    self.b_school_arrive[j].append(school_arr)
                    self.b_school_leave[j].append(school_dep)
                    self.b_station_return[j].append(return_arr)

                    self.bus_logs[j].append((self.b_station_arrive[j], depart, 0))
                    self.bus_logs[j].append((depart, school_arr, None))
                    self.bus_logs[j].append((school_arr, school_dep, 1))
                    self.bus_logs[j].append((school_dep, return_arr, None))

                    self.b_station_arrive[j] = return_arr
                    self.b[j] = 0

        self.queue_lengths.append((self.t, len(self.q)))

        if self.t >= self.simulation_time:
            self.late_students.extend(self.q)
            self.q.clear()
            return True

        self.t += 1
        return False

    def run(self):
        while not self.step():
            pass

class SimulationGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('School Bus Simulation')
        self.resize(1800, 1000)
        self.layout = QVBoxLayout()

        self.bus_label = QLabel('Number of Buses:')
        self.bus_spinbox = QSpinBox()
        self.bus_spinbox.setRange(1, 20)
        self.bus_spinbox.setValue(5)

        self.offset_label = QLabel('Initial Arrival Times (comma separated):')
        self.offset_input = QLineEdit()
        self.offset_input.setPlaceholderText("0,0,300,600,900")

        self.start_button = QPushButton('Run Simulation')
        self.start_button.clicked.connect(self.run_simulation)

        self.tabs = QTabWidget()
        self.timeline_canvas = FigureCanvas(Figure(figsize=(14, 6)))
        self.queue_canvas = FigureCanvas(Figure(figsize=(14, 6)))
        self.tabs.addTab(self.timeline_canvas, "Bus Operation Timeline")
        self.tabs.addTab(self.queue_canvas, "Queue Length Over Time")

        self.table = QTableWidget()
        self.log_table = QTableWidget()
        self.late_log = QTextEdit()
        self.late_log.setReadOnly(True)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.bus_label)
        h_layout.addWidget(self.bus_spinbox)
        h_layout.addWidget(self.offset_label)
        h_layout.addWidget(self.offset_input)

        self.layout.addLayout(h_layout)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(QLabel("Boarding Log"))
        self.layout.addWidget(self.table)
        self.layout.addWidget(QLabel("Bus Operation Log"))
        self.layout.addWidget(self.log_table)
        self.layout.addWidget(QLabel("Late Students (couldn't board by 6600s)"))
        self.layout.addWidget(self.late_log)

        self.setLayout(self.layout)

    def run_simulation(self):
        n = self.bus_spinbox.value()
        try:
            initial_offsets = list(map(int, self.offset_input.text().split(',')))
            if len(initial_offsets) < n:
                initial_offsets += [0] * (n - len(initial_offsets))
            elif len(initial_offsets) > n:
                initial_offsets = initial_offsets[:n]
        except:
            initial_offsets = [0 for _ in range(n)]

        self.sim = BusSimulation(n, initial_offsets)
        self.sim.run()
        self.plot_timeline()
        self.plot_queue()
        self.fill_table()
        self.fill_log_table()
        self.display_late_students()

    def plot_timeline(self):
        ax = self.timeline_canvas.figure.subplots()
        ax.clear()
        colors = ['red', 'green', 'blue', 'purple', 'orange', 'cyan', 'magenta', 'brown', 'pink', 'gray']
        for j, log in enumerate(self.sim.bus_logs):
            color = colors[j % len(colors)]
            label = f"Bus {j}"
            for idx, (start, end, y) in enumerate(log):
                if y is not None:
                    ax.plot([start, end], [y, y], color=color, linewidth=2, label=label if idx == 0 else "")
                else:
                    ax.plot([start, end], [0, 1] if (idx % 4 == 1) else [1, 0], color=color, linestyle='--')
        ax.set_title("Bus Operation Timeline")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("State (0=Station, 1=School)")
        ax.legend()
        self.timeline_canvas.draw()

    def plot_queue(self):
        ax = self.queue_canvas.figure.subplots()
        ax.clear()
        times = [t for t, _ in self.sim.queue_lengths]
        lengths = [l for _, l in self.sim.queue_lengths]
        ax.plot(times, lengths, color='black')
        ax.set_title("Queue Length Over Time")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Queue Length")
        self.queue_canvas.draw()

    def fill_table(self):
        logs_sorted = sorted(self.sim.boarding_log, key=lambda x: x[0])
        rows = len(logs_sorted)
        self.table.setRowCount(rows)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Time", "Bus ID", "Departure Occupancy", "Student IDs"])

        for row, (t, bus_id, occupancy, students) in enumerate(logs_sorted):
            self.table.setItem(row, 0, QTableWidgetItem(str(t)))
            self.table.setItem(row, 1, QTableWidgetItem(str(bus_id)))
            self.table.setItem(row, 2, QTableWidgetItem(str(occupancy)))
            self.table.setItem(row, 3, QTableWidgetItem(", ".join(map(str, students))))

    def fill_log_table(self):
        total_rows = sum(len(times) for times in self.sim.b_station_leave)
        self.log_table.setRowCount(total_rows)
        self.log_table.setColumnCount(5)
        self.log_table.setHorizontalHeaderLabels(["Bus ID", "Station Leave", "School Arrive", "School Leave", "Station Arrive"])
        row = 0
        for j in range(self.sim.n):
            for k in range(len(self.sim.b_station_leave[j])):
                self.log_table.setItem(row, 0, QTableWidgetItem(str(j)))
                self.log_table.setItem(row, 1, QTableWidgetItem(str(self.sim.b_station_leave[j][k])))
                self.log_table.setItem(row, 2, QTableWidgetItem(str(self.sim.b_school_arrive[j][k])))
                self.log_table.setItem(row, 3, QTableWidgetItem(str(self.sim.b_school_leave[j][k])))
                self.log_table.setItem(row, 4, QTableWidgetItem(str(self.sim.b_station_return[j][k])))
                row += 1

    def display_late_students(self):
        late_text = f"Total Late Students: {len(self.sim.late_students)}\n"
        late_text += "IDs: " + ", ".join(str(sid) for sid, _ in self.sim.late_students)
        self.late_log.setPlainText(late_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimulationGUI()
    window.show()
    sys.exit(app.exec_())
