import gira_homeserver_api

class ClientSingleton:
    instance = None

    @staticmethod
    def create(host, port, username, password):
        if ClientSingleton.instance == None:
            ClientSingleton.instance = gira_homeserver_api.Client(
                    host,
                    int(port),
                    username,
                    password,
                )
        else:
            ClientSingleton.instance.host = host
            ClientSingleton.instance.port = int(port)
            ClientSingleton.instance.username = username
            ClientSingleton.instance.password = password

        return ClientSingleton.instance

    @staticmethod
    def getInstance():
        if ClientSingleton.instance != None:
            return ClientSingleton.instance
        
