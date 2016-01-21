import asyncio
from autobahn.asyncio import websocket
from collections import defaultdict
import http.cookies
import json

from .accounts import auth


HOST = 'localhost'
PORT = 3671
WSADDR = 'ws://{}:{}'.format(HOST, PORT)

peers = {}
ids = defaultdict(list)


class PushServer(websocket.WebSocketServerProtocol):

    def onConnect(self, request):
        cooka = http.cookies.SimpleCookie()
        cooka.load(request.headers.get('cookie', ''))
        if 'token' not in cooka or 'acid' not in cooka:
            raise websocket.http.HttpException(401, 'Some cookies missing')

        cv = {x: y.value for x, y in cooka.items()}
        current = auth.Current(cv.get('acid'), cv.get('token'))

        if not current.loggedin:
            raise websocket.http.HttpException(401, 'Unable to authenticate you')

        data = {'object': self, 'current': current.record}
        peers[request.peer] = data
        ids[current.record.id].append(data)

    def onClose(self, wasClean, code, reason):
        try:
            data = peers.pop(self.peer)
            ids[data['current'].id].remove(data)
        except (KeyError, ValueError):
            pass
            
        
def async_send(data):
    # Emit parsed['markup'] to parsed['ids']
    # parsed['ids'] can contain a LOT of ids, can be a problem
    # see Python's code for comments
    #TODO: Send object containing all data

    # We can re-run the loop every N seconds to guarantee content
    # delivery (thus checking for `undefined`)
    delivery = list(data.pop('ids'))
    jsoned = json.dumps(data)
    if data['action'] in {'message', 'feed', 'notification'}:
        for i, id_ in enumerate(delivery):
            try:
                for peer in ids[id_]:
                    peer['object'].sendMessage(bytes(jsoned, 'utf-8'))
                delivery[i] = None
            except KeyError:
                continue
    else:
        pass


if __name__ == '__main__':

    factory = websocket.WebSocketServerFactory(WSADDR, server='')
    factory.protocol = PushServer

    loop = asyncio.get_event_loop()
    coro = loop.create_server(factory, HOST, PORT)
    server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()
