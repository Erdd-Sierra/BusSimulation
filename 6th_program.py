import sys
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QLineEdit, QTextEdit
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# =========================================
# バスシミュレーションクラス
# =========================================
class BusSimulation:
    def __init__(self, n, initial_arrival_offsets):
        self.n = n
        self.initial_arrival_offsets = initial_arrival_offsets
        self.max_students = 900
        self.bus_capacity = 60
        self.simulation_time = 6600
        self.boarding_time_per_student = 1  # 1人あたりの乗車時間 (秒)
        self.is_boarding = [False for _ in range(n)]
        self.next_student_to_board = [None for _ in range(n)]
        self.boarding_progress = [0 for _ in range(n)]        
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
        self.student_arrival_at_school_log = {} # 学生IDをキーに学校到着時間を記録
        self.boarded_students_per_bus = [[] for _ in range(n)]
    
    # -------------------------------
    # 生徒の到着時間生成
    # -------------------------------
    def generate_arrival_times(self):
        arrival_times = []
        t = 0
        student_id = 0

        while len(arrival_times) < self.max_students:
            # 各時間帯で平均間隔とばらつきを設定
            if 0 <= t < 2400:
                base_interval = 48
                variation = 20     # ±20秒程度のばらつき
            elif 2400 <= t < 4200:
                base_interval = 2
                variation = 1      # ±1秒
            elif 4200 <= t < 4800:
                base_interval = 4
                variation = 2
            elif 4800 <= t < 6600:
                base_interval = 12
                variation = 5
            else:
                break

            # ばらつきを持たせた間隔を生成（負値防止）
            interval = max(1, int(random.gauss(base_interval, variation / 2)))
            # ガウス分布(mean=base_interval, sd=variation/2)

            t += interval
            arrival_times.append((student_id, t))
            student_id += 1

        return arrival_times[:self.max_students]

    # -------------------------------
    # シミュレーション進行
    # -------------------------------
    def step(self):
        while self.i < len(self.x) and self.x[self.i][1] == self.t:
            self.q.append(self.x[self.i])
            self.i += 1

        for j in range(self.n):
            if self.t >= self.b_station_arrive[j]:
                if self.b[j] == 0:
                    self.b_wait_start[j] = self.t
                    self.boarded_students_per_bus[j] = [] # 乗車リストを初期化
                    

                # 乗車中ではない場合、次の乗客をキューから取り出す
                if not self.is_boarding[j] and self.q:
                    self.next_student_to_board[j] = self.q.pop(0)
                    self.is_boarding[j] = True
                    self.boarding_progress[j] = 0

                # 乗車プロセスを進める
                if self.is_boarding[j]:
                    self.boarding_progress[j] += 1
                    # 乗車が完了した場合
                    if self.boarding_progress[j] >= self.boarding_time_per_student:
                        student_id = self.next_student_to_board[j][0]
                        self.b[j] += 1
                        self.student_log.append((self.next_student_to_board[j][0], j, self.t, 'board'))
                        self.boarded_students_per_bus[j].append(student_id)
                        self.is_boarding[j] = False
                        self.next_student_to_board[j] = None

                # 最大待機360秒 or 満車 or 空列で出発
                # (乗車プロセスが完了している or 満車 or 最大待機時間を超過)
                required_depart_time = self.t + self.b[j] * self.boarding_time_per_student
                if not self.is_boarding[j] and (self.b[j] == self.bus_capacity or not self.q or (self.t - self.b_wait_start[j] >= 360)):
                    depart = max(self.t, required_depart_time)
                    school_arr = depart + 900
                    school_dep = school_arr + 300
                    return_arr = school_dep + 900

                    self.b_station_leave[j].append(depart)
                    self.b_school_arrive[j].append(school_arr)
                    self.b_school_leave[j].append(school_dep)
                    self.b_station_return[j].append(return_arr)

                    self.bus_logs[j].append((self.b_station_arrive[j], depart, 0))
                    self.bus_logs[j].append((depart, school_arr, None))
                    self.bus_logs[j].append((school_arr, school_dep, 1))
                    self.bus_logs[j].append((school_dep, return_arr, None))

                    # 学生の学校到着時間をログに記録
                    for student_id in self.boarded_students_per_bus[j]:
                        self.student_arrival_at_school_log[student_id] = school_arr
                    self.boarding_log.append((depart, j, self.b[j], self.boarded_students_per_bus[j]))

                    self.b_station_arrive[j] = return_arr
                    self.b[j] = 0
        
        
        self.queue_lengths.append((self.t, len(self.q)))

        
        # シミュレーション終了時の処理
        if self.t >= self.simulation_time:
            # 学校に到着できなかった学生を特定
            for student_id, student_arrival_time in self.student_arrival_at_school_log.items():
                if student_arrival_time > self.simulation_time:
                    self.late_students.append(student_id)
            # バス停にまだ残っている学生も遅刻者とする
            for student_id, _ in self.q:
                self.late_students.append(student_id)
            self.q.clear()
            return True

        self.t += 1
        return False

    def run(self):
        while not self.step():
            pass

# =========================================
# GUI部
# ========================================
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
        self.layout.addWidget(QLabel("Late Students (couldn't arrive at school by 6600s)"))
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
        self.plot_arrival_distribution()
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

    # -------------------------------
    # 時間帯別到着人数分布の表示
    # -------------------------------
    def plot_arrival_distribution(self):
        
        # arrival_canvasを初期化（初回のみ）
        if not hasattr(self, 'arrival_canvas'):
            self.arrival_canvas = FigureCanvas(Figure(figsize=(14, 6)))
            self.tabs.addTab(self.arrival_canvas, "Arrival Distribution")

        ax = self.arrival_canvas.figure.subplots()
        ax.clear()

        bins = list(range(0, 6601, 300))  # 5分ごと区間
        arrival_times = [t for _, t in self.sim.x]

        ax.hist(arrival_times, bins=bins, alpha=0.7, color="blue", edgecolor='black')

        ax.set_title("Student Arrival Distribution by Time Zone")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Number of Arrivals (per 5 min)")
        self.arrival_canvas.draw()

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
        late_text += "IDs: " + ", ".join(str(sid) for sid in self.sim.late_students)
        self.late_log.setPlainText(late_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimulationGUI()
    window.show()
    sys.exit(app.exec_())
