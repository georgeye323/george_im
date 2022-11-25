import sys
import os
from typing import List


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from senguo_im.bury.services import push_msg_to_bury, build_push_sms_msg_list
from senguo_im.chat.models import SMSRecord
from senguo_im.core.db_configs import DBSession


if __name__ == '__main__':
    """将短信全部推送到队列中"""

    session = DBSession()

    offset, limit = 0, 1000
    all_records: List[SMSRecord] = []
    # 先筛选所有没有店铺的线索  最后将存在店铺的所有的线索进行删除
    while True:
        records: List[SMSRecord] = (
            session.query(SMSRecord)
            .order_by(SMSRecord.id.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        all_records += records

        offset += limit

        if len(records) < limit:
            break
    print(f"一共有{len(all_records)} 条线索需要同步")
    push_msg_list = build_push_sms_msg_list(all_records)
    push_msg_to_bury(push_msg_list)
