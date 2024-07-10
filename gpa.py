import requests
import time
from PIL import Image, ImageTk
from io import BytesIO
from tkinter import Tk, Label, Canvas, Scrollbar, Frame

import threading


class NWPUStudent:
    def __init__(self):
        self.session = requests.session()
        self.student_assoc = None
    def login(self,auto_refresh=False):
        #host = f"https://uis.nwpu.edu.cn/cas/login?service=https%3A%2F%2Fjwxt.nwpu.edu.cn%2Fstudent%2Fsso-login"
        #self.session.get(host)
        #public_key_url = "https://uis.nwpu.edu.cn/cas/jwt/publicKey"
        #public_key_response = self.session.get(public_key_url)
        #public_key = public_key_response.text

        qr_url = "https://uis.nwpu.edu.cn/cas/qr/init"
        qr_response = self.session.get(qr_url)
        qr_json = qr_response.json()
        timestamp = qr_json["data"]["qrCode"]["timestamp"]
        # 生成二维码
        print("请扫描二维码登录")
        qr_code_url = f"https://uis.nwpu.edu.cn/cas/qr/qrcode?r={timestamp}"

        qr_image = self.session.get(qr_code_url)
        window = Tk()
        def wait_for_login():
            # 检查登录状态
            while True:
                time.sleep(1)
                check_url = f"https://uis.nwpu.edu.cn/cas/qr/comet"
                check_response = self.session.post(check_url)
                check_json = check_response.json()
                if check_json["code"] == 1:
                    print("二维码过期")
                    # 重新获取二维码
                    if auto_refresh:
                        qr_response = self.session.get(qr_url)
                        qr_json = qr_response.json()
                        timestamp = qr_json["data"]["qrCode"]["timestamp"]
                        qr_code_url = f"https://uis.nwpu.edu.cn/cas/qr/qrcode?r={timestamp}"
                        qr_image = self.session.get(qr_code_url)
                        image = Image.open(BytesIO(qr_image.content))
                        img_tk = ImageTk.PhotoImage(image)

                        label.configure(image=img_tk)
                        label.image = img_tk
                        continue
                    else:
                        break
                if check_json["data"]["qrCode"]["status"]=="3":
                    apptoken = check_json["data"]["qrCode"]["apptoken"]
                    qr_code_key = check_json["data"]["stateKey"]
                    # 请求的URL
                    host = f"https://uis.nwpu.edu.cn/cas/login"
                    param = {
                        "service": "https://jwxt.nwpu.edu.cn/student/sso-login",
                        "qrCodeKey": qr_code_key,
                    }
                    request = self.session.get(host, allow_redirects = False, params=param)
                    if request.status_code!=302:
                        print("[1]登录失败")
                        break
                    # 获取cookie
                    redirect_url = request.headers["Location"]
                    request = self.session.get(redirect_url,allow_redirects = False)
                    if request.status_code!=302:
                        print("[2]登录失败")
                        break
                    request = self.session.get(request.headers["Location"],allow_redirects = False)
                    if request.status_code!=302:
                        print("[3]登录失败")
                        break
                    # 获取学生信息
                    print("登录成功")
                    self.student_assoc = self.get_student_info()
            
                    break
            window.quit()
        window.title("请用西北工业大学APP扫码登录")
        image = Image.open(BytesIO(qr_image.content))
        img_tk = ImageTk.PhotoImage(image)

        # 使用Label显示图片
        label = Label(window, image=img_tk)
        label.pack()
        wait_thread = threading.Thread(target=wait_for_login)
        wait_thread.start()
        window.mainloop()
        wait_thread.join()
        window.destroy()
        
    def get_student_info(self):
        url = "https://jwxt.nwpu.edu.cn/student/for-std/student-portrait/getStdInfo?bizTypeAssoc=2&cultivateTypeAssoc=1"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()["student"]["id"]
        else:
            return None
    def get_gpa_rank(self):
        if self.student_assoc == None:
            return None
        # 获取GPA信息
        url = "https://jwxt.nwpu.edu.cn/student/for-std/student-portrait/getMyGrades"
        params = {'studentAssoc': self.student_assoc}
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            return response.json()["stdGpaRankDto"]
        else:
            return None
    def get_all_courses(self):
        if self.student_assoc == None:
            return None
        url = "https://jwxt.nwpu.edu.cn/student/for-std/student-portrait/getMyGradesByProgram"
        params = {'studentAssoc': self.student_assoc}
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            json_data = response.json()
            all_courses = []
            if "model" in json_data and "moduleList" in json_data["model"]:
                for module in json_data["model"]["moduleList"]:
                    for course in module["allCourseList"]:
                        all_courses.append(course)
            if "model" in json_data and "outerCourseList" in json_data["model"]:
                for course in json_data["model"]["outerCourseList"]:
                    all_courses.append(course)
                return all_courses
        else:
            return None
if __name__ == "__main__":
    student = NWPUStudent()
    retry = 0
    while True:
        student.login(auto_refresh=True)
        if student.student_assoc != None:
            break
        retry += 1
        if retry > 3:
            print("登录失败")
            time.sleep(5)
            exit(1)
    gpa_rank = student.get_gpa_rank()
    all_courses = student.get_all_courses()

    window = Tk()

    # 创建Scrollbar
    scrollbar = Scrollbar(window)
    scrollbar.pack(side="right", fill="y")

    # 创建Canvas
    canvas = Canvas(window, yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)

    # 配置Scrollbar
    scrollbar.config(command=canvas.yview)

    # 在Canvas上创建Frame用于放置课程信息
    frame = Frame(canvas)
    window.update()  # 更新窗口以获取准确的尺寸
    canvas.create_window((0, 0), window=frame, anchor="nw")

    # 显示GPA排名（total gpa, rank）
    Label(frame, text=f"总GPA: {gpa_rank['gpa']}").grid(row=0, column=0)
    Label(frame, text=f"排名前GPA: {gpa_rank['beforeRankGpa']}").grid(row=0, column=1)
    Label(frame, text=f"排名后GPA: {gpa_rank['afterRankGpa']}").grid(row=0, column=2)
    Label(frame, text=f"排名: {gpa_rank['rank']}").grid(row=0, column=3)

    # 画一个表格显示所有课程信息
    for i, course in enumerate(all_courses, start=1):
        Label(frame, text=course["nameZh"]).grid(row=i, column=0)
        Label(frame, text=course["code"]).grid(row=i, column=1)
        Label(frame, text=course["gradeStr"]).grid(row=i, column=2)
        Label(frame, text=course["gp"]).grid(row=i, column=3)
        Label(frame, text=course["finalResultType"]).grid(row=i, column=4)

    # 更新Canvas的滚动区域以适应Frame的大小
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))
    window.title("西北工业大学学生成绩查询")
    window.mainloop()
