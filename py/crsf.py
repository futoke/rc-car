from enum import Enum


CRSF_SYNC = 0xC8
PACKET_LENGTH = 24
CHANNEL_LENGTH = 11
CHANNELS_NUM = 16


class PacketsTypes(int, Enum):
    GPS = 0x02
    VARIO = 0x07
    BATTERY_SENSOR = 0x08
    BARO_ALT = 0x09
    HEARTBEAT = 0x0B
    VIDEO_TRANSMITTER = 0x0F
    LINK_STATISTICS = 0x14
    RC_CHANNELS_PACKED = 0x16
    ATTITUDE = 0x1E
    FLIGHT_MODE = 0x21
    DEVICE_INFO = 0x29
    CONFIG_READ = 0x2C
    CONFIG_WRITE = 0x2D
    RADIO_ID = 0x3A


def crc8_dvb_s2(crc, a) -> int:
  crc = crc ^ a
  for _ in range(8):
    if crc & 0x80:
      crc = (crc << 1) ^ 0xD5
    else:
      crc = crc << 1
  return crc & 0xFF


def crc8_data(data) -> int:
    crc = 0
    for a in data:
        crc = crc8_dvb_s2(crc, a)
    return crc


def crsf_validate_frame(frame) -> bool:
    return crc8_data(frame[2:-1]) == frame[-1]


def signed_byte(b):
    return b - 256 if b >= 128 else b


def pack_CRSF_to_bytes(channels) -> bytes:
    # Channels is in CRSF format! (0-1984)
    # Values are packed little-endianish
    # such that bits BA987654321 -> 87654321, 00000BA9
    # 11 bits per channel x 16 channels = 22 bytes
    if len(channels) != CHANNELS_NUM:
        raise ValueError(f"CRSF must have {CHANNELS_NUM} channels")
    
    result = bytearray()
    dest_shift = 0
    new_value = 0
    for ch in channels:
        # Put the low bits in any remaining dest capacity.
        new_value |= (ch << dest_shift) & 0xff
        result.append(new_value)

        # Shift the high bits down and place them into the next dest byte.
        src_bits_left = CHANNEL_LENGTH - 8 + dest_shift
        new_value = ch >> (CHANNEL_LENGTH - src_bits_left)
        # When there's at least a full byte remaining, consume that as well.
        if src_bits_left >= 8:
            result.append(new_value & 0xff)
            new_value >>= 8
            src_bits_left -= 8

        # Next dest should be shifted up by the bits consumed.
        dest_shift = src_bits_left

    return result


def channels_CRSF_to_packet(channels) -> bytes:
    result = bytearray([
        CRSF_SYNC, PACKET_LENGTH, PacketsTypes.RC_CHANNELS_PACKED
    ])
    result += pack_CRSF_to_bytes(channels)
    result.append(crc8_data(result[2:]))
    
    return result


def handle_CRSF_packet(ptype, data):
    match ptype:
        case PacketsTypes.RADIO_ID:
            if data[5] == 0x10:
                # print(f"OTX sync")
                pass

        case PacketsTypes.LINK_STATISTICS:
            rssi1 = signed_byte(data[3])
            rssi2 = signed_byte(data[4])
            lq = data[5]
            snr = signed_byte(data[6])
            antenna = data[7]
            mode = data[8]
            power = data[9]

            # Telemetry strength.
            downlink_rssi = signed_byte(data[10])
            downlink_lq = data[11]
            downlink_snr = signed_byte(data[12])
            print(
                f"RSSI={rssi1}/{rssi2}dBm LQ={lq:03} mode={mode} "
                f"ant={antenna} snr={snr} power={power} drssi={downlink_rssi} "
                f"dlq={downlink_lq} dsnr={downlink_snr}"
            )
        
        case PacketsTypes.ATTITUDE:
            pitch = int.from_bytes(data[3:5], byteorder="big", signed=True) / 10000.0
            roll = int.from_bytes(data[5:7], byteorder="big", signed=True) / 10000.0
            yaw = int.from_bytes(data[7:9], byteorder="big", signed=True) / 10000.0
            print(f"Attitude: Pitch={pitch:0.2f} Roll={roll:0.2f} Yaw={yaw:0.2f} (rad)")

        case PacketsTypes.FLIGHT_MODE:
            packet = "".join(map(chr, data[3:-2]))
            print(f"Flight Mode: {packet}")

        case PacketsTypes.BATTERY_SENSOR:
            vbat = int.from_bytes(data[3:5], byteorder="big", signed=True) / 10.0
            curr = int.from_bytes(data[5:7], byteorder="big", signed=True) / 10.0
            mah = data[7] << 16 | data[8] << 7 | data[9]
            pct = data[10]
            print(f"Battery: {vbat:0.2f}V {curr:0.1f}A {mah}mAh {pct}%")

        case PacketsTypes.BARO_ALT:
            print(f"BaroAlt: ")

        case PacketsTypes.DEVICE_INFO:
            packet = " ".join(map(hex, data))
            print(f"Device Info: {packet}")

        case PacketsTypes.VARIO:
            vspd = int.from_bytes(data[3:5], byteorder="big", signed=True) / 10.0
            print(f"VSpd: {vspd:0.1f}m/s")
        
        case PacketsTypes.RC_CHANNELS_PACKED:
            # print(f"Channels: (data)")
            pass
        
        case _:
            packet = " ".join(map(hex, data))
            print(f"Unknown 0x{ptype:02x}: {packet}")
