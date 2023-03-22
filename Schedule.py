from queue import Queue
import heapq


def log(content, clear=False):
    """
    打印每一帧的日志
    :param content: 打印内容
    :param clear: 是否清空文件
    """
    # pass
    with open("log.txt", mode='a+', encoding='utf-8') as file:
        if clear:
            file.truncate(0)
        file.write(str(content))
        file.write("\n")


class Job:
    __slots__ = ['start', 'key', 'speed_angular', 'speed_linear', 'exist', 'start_func']

    def __init__(self, start, robot_id, job_key, speed_angular, speed_linear, start_func):
        self.start = start
        self.key = (robot_id, job_key, start)
        self.speed_angular = speed_angular
        self.speed_linear = speed_linear
        self.exist = True
        self.start_func = start_func

    def __lt__(self, other):
        return self.start < other.start

    def do_start_func(self):
        self.start_func(self)

    def cancel(self):
        self.exist = False

    def is_exist(self):
        return self.exist

    def __str__(self) -> str:
        return " ".join(str(item) for item in (self.start, self.key))


class Schedule:
    __slots__ = ['jobs_start', 'job_record']

    def __init__(self):
        self.jobs_start = []
        self.job_record = {}  # 有无

    def add_job(self, job):
        """
        增加一项任务
        :param job: 任务描述
        """
        if job.key not in self.job_record.keys():
            heapq.heappush(self.jobs_start, job)
            self.job_record[job.key] = job

    def cancel_job(self, job):
        """
        取消该项任务
        :param job: 任务描述
        """
        if job.key in self.job_record.keys():
            self.job_record[job.key].cancel()
            del self.job_record[job.key]

    def update_job(self, job):
        """
        更新该项任务
        :param job: 任务描述
        """
        self.cancel_job(job)
        self.add_job(job)

    def running(self, fid):
        while len(self.jobs_start) > 0 and self.jobs_start[0].start == fid:
            job = heapq.heappop(self.jobs_start)
            if job.is_exist() and job.start_func is not None:
                job.do_start_func()
        self.echo()

    def echo(self):
        for job in self.jobs_start:
            pass
            # log(job)


# def start_task(job):
#     print(str(job.id), "start")
#
#
# def stop_task(job):
#     print(str(job.id), "stop")


if __name__ == '__main__':
    s = Schedule()
    array = [10, 17, 50, 7, 30, 24, 27, 45, 15, 5, 36, 21]
    for i in array:
        job1 = Job(i, i, i + 1, 10, 11, None)
        s.add_job(job1)

    # job1 = Job(0, 11, 50, 51, 10, 11, start_task, stop_task)
    # s.update_job(job1)
    s.echo()
    print("\n")
    for i in range(1, 8):
        print(i)
        s.running(i)

    s.echo()
