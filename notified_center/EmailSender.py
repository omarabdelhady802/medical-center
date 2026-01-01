import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.hostinger.com"
SMTP_PORT = 465
IMAP_SERVER = "imap.hostinger.com"
IMAP_PORT = 993

class EmailClient:
    def __init__(self, smtp_server=SMTP_SERVER, smtp_port=SMTP_PORT,
                 imap_server=IMAP_SERVER, imap_port=IMAP_PORT):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port

    # =========================
    # SMTP Send
    # =========================
    def send_email(self, subject, body):
        sender = "kenzy.gaber@revyai.tech"
        password = "01554019172Ra@"
        final_body = "machine ip 194.5.157.240:  and port 2005 " + body
        try:
            receivers = ["omarabdelhady802@gmail.com", "m.a.ragab2005@gmail.com","yh2767058@gmail.com"]
            for receiver in receivers:
                msg = MIMEMultipart()
                msg["From"] = sender
                msg["To"] = receiver
                msg["Subject"] = subject
                msg.attach(MIMEText(final_body, "plain"))


                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
                server.login(sender, password)
                server.send_message(msg)
                server.quit()


        except Exception as e:
            print("SMTP Error:", e)

    