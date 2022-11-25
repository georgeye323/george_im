import datetime
import os
import sys
import traceback

import sentry_sdk
from celery import Celery
from celery.schedules import crontab
from sentry_sdk.integrations.celery import CeleryIntegration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from senguo_im.chat.models import SMSRecord
from senguo_im.chat.services import list_room_message_by_unread, create_sms_record
from senguo_im.core.db_configs import scoped_DBSession
from senguo_im.core.yunpian.yunpian import YunPainFunc
from senguo_im.settings import RABBITMQ_BROKE, SENTRY_DSN
from senguo_im.user.services import list_user_by_passport_ids
from senguo_im.bury.services import build_push_sms_msg_list, push_msg_to_bury


app = Celery("im_auto_work", broker=RABBITMQ_BROKE, backend="")
app.conf.CELERY_TIMEZONE = "Asia/Shanghai"  # 时区
app.conf.CELERYD_CONCURRENCY = 1  # 任务并发数
app.conf.CELERYD_TASK_SOFT_TIME_LIMIT = 60  # 任务超时时间
app.conf.CELERY_DISABLE_RATE_LIMITS = True  # 任务频率限制开关

app.conf.CELERYBEAT_SCHEDULE = {
    "auto_check_unread_msg": {
        "task": "auto_check_unread_msg",
        "schedule": crontab(hour="0,6,18", minute=0),
        "options": {"queue": "im_auto_work"},
    },
}
sentry_sdk.init(SENTRY_DSN, integrations=[CeleryIntegration()])


# 自动检查未读消息，并批量发送短信
@app.task(bind=True, name="auto_check_unread_msg")
def auto_check_unread_msg(self,):
    """
    规则：
        一天3次通知，间隔6小时，每次统计前12h~前6小时，凌晨12点~6点不统计
    """
    now_hour = datetime.datetime.now().strftime("%Y-%m-%d %H") + ":00:00"
    now_hour = datetime.datetime.strptime(now_hour, "%Y-%m-%d %H:%M:%S")
    from_date = now_hour + datetime.timedelta(hours=-12)
    to_date = now_hour + datetime.timedelta(hours=-6)
    session = scoped_DBSession()
    try:
        # 获取发送目标
        rooms = list_room_message_by_unread(session, from_date, to_date)
        admin_list = []
        customer_list = []
        for room in rooms:
            # 判断是否有采购商未读消息
            if len(room.passport_ids) > 1 or room.apply_passport_id not in room.passport_ids:
                customer_list.append(room.apply_passport_id)
            # 判断是否有管理员未读消息
            if room.apply_passport_id in room.passport_ids:
                members = eval(room.members)
                members.remove(room.apply_passport_id)
                admin_list += members
        admin_users = list_user_by_passport_ids(session, set(admin_list))
        customer_users = list_user_by_passport_ids(session, set(customer_list))
        # 过滤未绑手机号用户
        admin_users = [user for user in admin_users if user.phone]
        customer_users = [user for user in customer_users if user.phone]
        admin_phone_list = [user.phone for user in admin_users]
        customer_phone_list = [user.phone for user in customer_users]
        sms_record_list = []
        if admin_phone_list:
            # 发送短信给店铺管理员
            admin_sms = YunPainFunc.asyn_send_unread_msg(
                YunPainFunc.sms_text_pfy,
                admin_phone_list,
                YunPainFunc.sms_sign_pfy,
                YunPainFunc.sms_callback_pfy,
                "app",
            )
            admin_sms = admin_sms.get("data", [])
            admin_sms_dict = {i.get("mobile"): i for i in admin_sms}
            # 短信发送记录
            for user in admin_users:
                send_data = admin_sms_dict.get(user.phone, {})
                ar = dict(passport_id=user.passport_id, phone=user.phone, send_type=1)
                if send_data.get("code") == 0 and send_data.get("count", 0) != 0:
                    ar["fact_sms_count"] = int(send_data.get("count", 0))
                    ar["record_status"] = 1
                    ar["yunpian_sid"] = send_data.get("sid", 0)
                else:
                    ar["record_status"] = 3
                    ar["remark"] = send_data.get("msg", "")
                sms_record_list.append(ar)
        if customer_phone_list:
            # 发送短信给采购商
            customer_sms = YunPainFunc.asyn_send_unread_msg(
                YunPainFunc.sms_text_cgzs,
                customer_phone_list,
                YunPainFunc.sms_sign_cgzs,
                YunPainFunc.sms_callback_cgzs,
                "wx",
            )
            customer_sms = customer_sms.get("data", [])
            customer_sms_dict = {i.get("mobile"): i for i in customer_sms}
            # 短信发送记录
            for user in customer_users:
                _send_data = customer_sms_dict.get(user.phone, {})
                cr = dict(passport_id=user.passport_id, phone=user.phone, send_type=2)
                if _send_data.get("code") == 0 and _send_data.get("count", 0) != 0:
                    cr["fact_sms_count"] = int(_send_data.get("count", 0))
                    cr["record_status"] = 1
                    cr["yunpian_sid"] = _send_data.get("sid", 0)
                else:
                    cr["record_status"] = 3
                    cr["remark"] = _send_data.get("msg", "")
                sms_record_list.append(cr)
        push_sms_record_list = []
        for sms_record in sms_record_list:
            new_r = create_sms_record(session, sms_record)
            push_sms_record_list.append(new_r)
        if sms_record_list:
            # session.bulk_insert_mappings(SMSRecord, sms_record_list)
            session.commit()
            # 推送至 bury统计
            push_msg_list = build_push_sms_msg_list(push_sms_record_list)
            push_msg_to_bury(push_msg_list)
    except:
        print(traceback.format_exc())
        raise ValueError(traceback.format_exc())
    finally:
        session.close()
