import asyncio
import websockets

# Diccionario para manejar los clientes conectados.
clientes = {}

# Diccionario para almacenar historial de mensajes grupales y privados.
historial_grupal = []
historial_privado = {}

# Esta función maneja cada nueva conexión de cliente.
async def manejar_conexion(websocket, path):
    # Recibir el apodo del cliente
    nickname = await websocket.recv()
    
    # Asegúrate de que el apodo sea único.
    while nickname in clientes:
        await websocket.send("Nickname already in use. Try another one.")
        nickname = await websocket.recv()
    
    # Añadir el cliente a la lista de usuarios conectados.
    clientes[nickname] = websocket
    print(f"{nickname} connected.")
    
    # Notificar a todos los usuarios que un nuevo usuario se ha conectado.
    await enviar_a_todos(f"{nickname} has connected.")
    
    # Enviar el historial grupal al nuevo usuario.
    await enviar_historial_grupal(websocket)
    
    # Enviar la lista actualizada de usuarios en línea a todos los clientes.
    await enviar_lista_usuarios()

    try:
        while True:
            mensaje = await websocket.recv()
            
            # Verificar si es un mensaje privado.
            if mensaje.startswith("/privado"):
                partes = mensaje.split(' ', 2)
                if len(partes) < 3:
                    await websocket.send("Incorrect command. Use: /privado username message")
                else:
                    destinatario = partes[1]
                    mensaje_privado = partes[2]
                    
                    # Si el destinatario existe, enviar mensaje privado.
                    if destinatario in clientes:
                        await enviar_privado(nickname, destinatario, mensaje_privado)
                    else:
                        # Guardar el mensaje privado si el destinatario no está conectado.
                        await guardar_historial_privado(nickname, destinatario, mensaje_privado)
                        await websocket.send(f"User {destinatario} not found. Message saved.")
            else:
                # Mensaje grupal.
                mensaje_grupal = f"{nickname}: {mensaje}"
                historial_grupal.append(mensaje_grupal)
                await enviar_a_todos(mensaje_grupal)
    
    except websockets.ConnectionClosed:
        print(f"{nickname} disconnected.")
    
    finally:
        # Eliminar el cliente de la lista.
        del clientes[nickname]
        await enviar_a_todos(f"{nickname} has disconnected.")
        
        # Enviar la lista actualizada de usuarios a todos los clientes.
        await enviar_lista_usuarios()

# Función para enviar un mensaje a todos los clientes conectados.
async def enviar_a_todos(mensaje):
    if clientes:
        await asyncio.gather(*[cliente.send(mensaje) for cliente in clientes.values()])

# Función para enviar un mensaje privado.
async def enviar_privado(remitente, destinatario, mensaje):
    # Guardar el mensaje en el historial privado.
    await guardar_historial_privado(remitente, destinatario, mensaje)

    if destinatario in clientes:
        await clientes[destinatario].send(f"(Private from {remitente}): {mensaje}")
        await clientes[remitente].send(f"(Private to {destinatario}): {mensaje}")
    else:
        await clientes[remitente].send(f"User {destinatario} not found. Message saved.")

# Función para guardar el historial de mensajes privados.
async def guardar_historial_privado(remitente, destinatario, mensaje):
    if remitente not in historial_privado:
        historial_privado[remitente] = {}
    if destinatario not in historial_privado:
        historial_privado[destinatario] = {}

    if destinatario not in historial_privado[remitente]:
        historial_privado[remitente][destinatario] = []
    if remitente not in historial_privado[destinatario]:
        historial_privado[destinatario][remitente] = []
    
    historial_privado[remitente][destinatario].append(f"(Private to {destinatario}): {mensaje}")
    historial_privado[destinatario][remitente].append(f"(Private from {remitente}): {mensaje}")

# Función para enviar el historial grupal a un cliente específico.
async def enviar_historial_grupal(cliente):
    for mensaje in historial_grupal:
        await cliente.send(mensaje)

# Función para enviar la lista de usuarios conectados.
async def enviar_lista_usuarios():
    if clientes:
        usuarios_en_linea = f"Online users: {', '.join(clientes.keys())}"
        await asyncio.gather(*[cliente.send(usuarios_en_linea) for cliente in clientes.values()])

# Iniciar el servidor WebSocket.
start_server = websockets.serve(manejar_conexion, "localhost", 12345)

# Ejecutar el servidor indefinidamente.
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
