import json
import ssl
import time
import os
import paho.mqtt.client as mqtt


class MQTTClient:
    def __init__(
        self,
        host,
        port,
        topic=None,
        client_id=None,
        username=None,
        password=None,
        use_tls=False,
        use_websocket=False,
        ws_path="/mqtt",
        keepalive=60,
    ):
        self.host = host
        self.port = port
        self.topic = topic
        self.keepalive = keepalive
        self.debug = os.getenv("SIM_MQTT_DEBUG", "0").lower() in {"1", "true", "yes", "on"}

        transport = "websockets" if use_websocket else "tcp"
        self.client = mqtt.Client(client_id=client_id, transport=transport)

        # Authentication
        if username and password:
            self.client.username_pw_set(username, password)

        # TLS
        if use_tls:
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
            self.client.tls_insecure_set(False)

        # WebSocket path
        if use_websocket:
            self.client.ws_set_options(path=ws_path)

        # Auto reconnect config
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe
        self.client.on_message = self._on_message

        self._connected = False

    # --------------------------------------------------
    # Connection Handling
    # --------------------------------------------------

    def connect(self):
        self.client.connect(self.host, self.port, self.keepalive)
        self.client.loop_start()

        # Wait until connected (optional but useful)
        timeout = 5
        start = time.time()
        while not self._connected and time.time() - start < timeout:
            time.sleep(0.1)

        if not self._connected:
            self.client.loop_stop()
            self.client.disconnect()
            raise ConnectionError("MQTT connection failed")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    # --------------------------------------------------
    # Publish
    # --------------------------------------------------

    def publish(self, payload, topic=None, qos=0, retain=False):
        if self.debug:
            print(f"DEBUG: Passed topic arg: '{topic}' | Default topic: '{self.topic}'")
        topic = topic or self.topic
        if topic is None:
            raise ValueError("No topic specified")

        result = self.client.publish(
            topic,
            json.dumps(payload),
            qos=qos,
            retain=retain,
        )

        return result.rc

    # --------------------------------------------------
    # Subscribe
    # --------------------------------------------------

    def subscribe(self, topic, qos=0):
        self.client.subscribe(topic, qos=qos)

    # --------------------------------------------------
    # Callbacks
    # --------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            print(f"[MQTT] Connected to {self.host}:{self.port}")
        else:
            print(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        print(f"[MQTT] Disconnected (code={rc})")

    def _on_publish(self, client, userdata, mid):
        pass  # Optional: enable for debugging

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        print(f"[MQTT] Subscribed (mid={mid})")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"[MQTT] Message received on {msg.topic}: {payload}")
        except Exception:
            print(f"[MQTT] Raw message on {msg.topic}: {msg.payload}")