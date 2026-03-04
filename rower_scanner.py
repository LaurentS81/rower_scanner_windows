import asyncio
import socket
from bleak import BleakScanner, BleakClient

# --- CONFIG ---
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
FTMS_MEASUREMENT_UUID = "00002ad1-0000-1000-8000-00805f9b34fb"
FTMS_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb"

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def parse_ftms(data: bytearray):
    """
    Indoor Rowing Data (2AD1)
    """
    flags = int.from_bytes(data[0:2], "little")
    index = 2

    speed = 0.0
    cadence = 0.0

    # Bit 0 : vitesse instantanée présente
    if flags & 0x0001:
        raw_speed = int.from_bytes(data[index:index+2], "little")
        speed = raw_speed / 100.0  # m/s
        index += 2

    # Bit 6 : cadence (strokes per minute)
    if flags & 0x0040:
        raw_cadence = int.from_bytes(data[index:index+2], "little")
        cadence = raw_cadence / 2.0
        index += 2

    return cadence, speed


async def main():
    print("🔍 Scan BLE...")
    devices = await BleakScanner.discover()

    ftms_device = None
    for d in devices:
        if d.metadata and "uuids" in d.metadata:
            if FTMS_SERVICE_UUID.lower() in [u.lower() for u in d.metadata["uuids"]]:
                ftms_device = d
                break

    if not ftms_device:
        print("❌ Aucun rameur FTMS trouvé")
        return

    print(f"✅ Rameur trouvé : {ftms_device.name}")

    async with BleakClient(ftms_device) as client:
        print("🔗 Connecté")

        def notification_handler(sender, data):
            hexdata = " ".join(f"{b:02X}" for b in data)
            flags = int.from_bytes(data[0:2], "little")
            print(f"RAW [{len(data)} bytes] flags=0x{flags:04X} → {hexdata}")

        # 1️⃣ S'abonner aux mesures
        await client.start_notify(FTMS_MEASUREMENT_UUID, notification_handler)
        print("📡 Notifications FTMS activées")

        # 2️⃣ Request Control
        await client.write_gatt_char(
            FTMS_CONTROL_POINT_UUID,
            bytearray([0x00]),
            response=True
        )
        print("🟢 FTMS Control accordé")

        await asyncio.sleep(0.5)

        # 3️⃣ Start
        await client.write_gatt_char(
            FTMS_CONTROL_POINT_UUID,
            bytearray([0x07]),
            response=True
        )
        print("▶️ FTMS Start envoyé")

        print("📡 En attente des données (Ctrl+C pour arrêter)")
        while True:
            await asyncio.sleep(1)


asyncio.run(main())
