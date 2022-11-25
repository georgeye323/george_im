from collections import defaultdict


class RoomHandler(object):
    def __init__(self):
        # 房间信息 {room_id:[client_id_list],}
        self.rooms_info = defaultdict(list)
        # 客户端信息 {client_id:{'conn':ws_conn, 'room_ids': [],}
        self.clients_info = defaultdict(list)

    def add_room(self, passport_id: int, room_ids: list):
        for room_id in room_ids:
            if passport_id not in self.rooms_info[room_id]:
                self.rooms_info[room_id].append(passport_id)

    def remove_room(self, passport_id: int, room_ids: list):
        for room_id in room_ids:
            if passport_id in self.rooms_info[room_id]:
                self.rooms_info[room_id].remove(passport_id)

    def new_room(self, room_id: int, member_list: list):
        self.rooms_info[room_id] = member_list

    def add_client(self, passport_id: int, ws_conn: object):
        """
        添加client_ws_conn
        考虑多端登录，需要存储list
        """
        # 添加连接信息
        if ws_conn not in self.clients_info[passport_id]:
            self.clients_info[passport_id].append(ws_conn)

    def remove_client(self, passport_id: int, ws_conn: object):
        """
        移除client_ws_conn
        """
        if ws_conn in self.clients_info[passport_id]:
            self.clients_info[passport_id].remove(ws_conn)


room_handler = RoomHandler()
