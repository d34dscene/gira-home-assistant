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

        return ClientSingleton.instance

    @staticmethod
    def getInstance():
        if ClientSingleton.instance != None:
            return ClientSingleton.instance
        
