import serial
import serial.tools.list_ports

# Test common baudrates
baudrates = [
    9600,
    19200,
    38400,
    57600,
    115200,
    250000,
    500000,
    1000000,
]


def check_baudrates(port):
    """Check common baudrates for a given port"""
    print(f"Testing baudrates for port: {port}")

    for baudrate in baudrates:
        try:
            with serial.Serial(port, baudrate, timeout=1) as ser:
                print(f"✓ Baudrate {baudrate}: Connection successful")
                # You can try to read/write here to test if it's the correct baudrate
                # ser.write(b'test')
                # response = ser.read(10)
        except serial.SerialException as e:
            print(f"✗ Baudrate {baudrate}: Failed - {e}")
        except Exception as e:
            print(f"✗ Baudrate {baudrate}: Error - {e}")


# List available ports first
def list_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"Port: {port.device}")
        print(f"  Description: {port.description}")
        print(f"  Hardware ID: {port.hwid}")
        print()


def comprehensive_port_check():
    """Comprehensive check of all serial ports"""
    ports = serial.tools.list_ports.comports()

    for port in ports:
        print(f"\n{'='*50}")
        print(f"Port: {port.device}")
        print(f"Description: {port.description}")
        print(f"Hardware ID: {port.hwid}")
        print(f"Manufacturer: {port.manufacturer}")
        print(f"Product: {port.product}")
        print(f"Serial Number: {port.serial_number}")

        working_baudrates = []

        for baudrate in baudrates:
            try:
                ser = serial.Serial(port.device, baudrate, timeout=0.5)
                ser.close()
                working_baudrates.append(baudrate)
            except:
                pass

        print(f"Working baudrates: {working_baudrates}")


def check_feetech_motor_baudrate(port, motor_id=1):
    """Check current baudrate setting of a Feetech motor"""
    from lerobot.common.motors.feetech.tables import (
        STS_SMS_SERIES_BAUDRATE_TABLE,
        SCS_SERIES_BAUDRATE_TABLE,
        MODEL_NUMBER_TABLE,
    )

    print(f"\nChecking Feetech motor baudrate on port: {port}")
    print(f"Target motor ID: {motor_id}")

    # Feetech baudrate value to actual baudrate mapping
    feetech_baudrates = {
        0: 1_000_000,
        1: 500_000,
        2: 250_000,
        3: 128_000,
        4: 115_200,
        5: 57_600,
        6: 38_400,
        7: 19_200,
    }

    successful_communications = []

    # Try each baudrate to find the motor
    for test_baudrate in [1_000_000, 500_000, 250_000, 128_000, 115_200, 57_600, 38_400, 19_200]:
        try:
            print(f"Testing communication at {test_baudrate} baud...")

            import scservo_sdk as scs

            port_handler = scs.PortHandler(port)
            packet_handler = scs.PacketHandler(0)  # Protocol 0

            if not port_handler.openPort():
                print(f"Failed to open port at {test_baudrate}")
                continue

            port_handler.setBaudRate(test_baudrate)

            # Try to ping the motor
            model_number, comm, error = packet_handler.ping(port_handler, motor_id)

            if comm == scs.COMM_SUCCESS and error == 0:
                print(f"✓ Motor responds at {test_baudrate} baud!")

                # Read the baudrate register (address 6)
                baudrate_value, comm2, error2 = packet_handler.read1ByteTxRx(port_handler, motor_id, 6)

                if comm2 == scs.COMM_SUCCESS and error2 == 0:
                    configured_baudrate = feetech_baudrates.get(baudrate_value, "Unknown")
                    
                    print(f"  Motor baudrate register value: {baudrate_value}")
                    print(f"  Register corresponds to baudrate: {configured_baudrate}")
                    
                    if test_baudrate == configured_baudrate:
                        print(f"  ✓ Communication baudrate matches configured baudrate")
                    else:
                        print(f"  ⚠️  Communication baudrate ({test_baudrate}) differs from configured ({configured_baudrate})")
                        print(f"     This could indicate:")
                        print(f"     - Baudrate register is incorrect/outdated")
                        print(f"     - Motor has baudrate tolerance allowing different rates")
                        print(f"     - Motor firmware auto-detection is active")

                    # Read model number for identification
                    print(f"  Motor model number: {model_number}")

                    # Find model name
                    model_name = "Unknown"
                    for name, num in MODEL_NUMBER_TABLE.items():
                        if num == model_number:
                            model_name = name
                            break
                    print(f"  Motor model: {model_name}")
                    
                    successful_communications.append({
                        'communication_baudrate': test_baudrate,
                        'configured_baudrate': configured_baudrate,
                        'register_value': baudrate_value,
                        'model_number': model_number,
                        'model_name': model_name
                    })
                else:
                    print(f"  Failed to read baudrate register: comm={comm2}, error={error2}")
                    successful_communications.append({
                        'communication_baudrate': test_baudrate,
                        'configured_baudrate': 'Unable to read',
                        'register_value': None,
                        'model_number': model_number,
                        'model_name': 'Unknown'
                    })

            port_handler.closePort()

        except ImportError:
            print("Error: scservo_sdk not installed. Please install it with:")
            print("pip install scservo_sdk")
            return None
        except Exception as e:
            print(f"Error testing {test_baudrate}: {e}")
            continue

    if successful_communications:
        print(f"\n--- SUMMARY ---")
        print(f"Motor ID {motor_id} responds at {len(successful_communications)} different baudrate(s):")
        for comm in successful_communications:
            match_status = "✓ MATCH" if comm['communication_baudrate'] == comm['configured_baudrate'] else "⚠️ DIFFERENT"
            print(f"  Communication: {comm['communication_baudrate']:>9} | Configured: {comm['configured_baudrate']:>9} | {match_status}")
        
        # Return the first successful communication
        return successful_communications[0]
    else:
        print("Motor not found at any baudrate")
        return None


def scan_feetech_bus(port):
    """Scan for all Feetech motors on the bus"""
    from lerobot.common.motors.feetech.tables import MODEL_NUMBER_TABLE

    print(f"\nScanning Feetech bus on port: {port}")

    feetech_baudrates = [
        1_000_000,
        500_000,
        250_000,
        128_000,
        115_200,
        57_600,
        38_400,
        19_200,
    ]

    found_motors = {}

    for test_baudrate in feetech_baudrates:
        try:
            print(f"\nScanning at {test_baudrate} baud...")

            import scservo_sdk as scs

            port_handler = scs.PortHandler(port)
            packet_handler = scs.PacketHandler(0)  # Protocol 0

            if not port_handler.openPort():
                continue

            port_handler.setBaudRate(test_baudrate)

            # Try to ping IDs 1-20 (common range)
            motors_at_baudrate = []
            for motor_id in range(1, 21):
                model_number, comm, error = packet_handler.ping(
                    port_handler, motor_id
                )

                if comm == scs.COMM_SUCCESS and error == 0:
                    # Find model name
                    model_name = "Unknown"
                    for name, num in MODEL_NUMBER_TABLE.items():
                        if num == model_number:
                            model_name = name
                            break

                    motor_info = {
                        "id": motor_id,
                        "model_number": model_number,
                        "model_name": model_name,
                        "baudrate": test_baudrate,
                    }
                    motors_at_baudrate.append(motor_info)
                    print(
                        f"  Found motor ID {motor_id}: {model_name} (model #{model_number})"
                    )

            if motors_at_baudrate:
                found_motors[test_baudrate] = motors_at_baudrate

            port_handler.closePort()

        except ImportError:
            print("Error: scservo_sdk not installed. Please install it with:")
            print("pip install scservo_sdk")
            return None
        except Exception as e:
            print(f"Error scanning at {test_baudrate}: {e}")
            continue

    print(
        f"\nScan complete. Found {sum(len(motors) for motors in found_motors.values())} motors total."
    )
    return found_motors


def check_feetech_motor_detailed(port, motor_id=1):
    """Get detailed information about a Feetech motor including baudrate"""
    try:
        import scservo_sdk as scs
        from lerobot.common.motors.feetech.tables import (
            MODEL_NUMBER_TABLE,
            STS_SMS_SERIES_CONTROL_TABLE,
            SCS_SERIES_CONTROL_TABLE,
        )

        print(
            f"\nDetailed Feetech motor check on port: {port}, ID: {motor_id}"
        )

        feetech_baudrates = [
            1_000_000,
            500_000,
            250_000,
            128_000,
            115_200,
            57_600,
            38_400,
            19_200,
        ]
        baudrate_values = {
            0: 1_000_000,
            1: 500_000,
            2: 250_000,
            3: 128_000,
            4: 115_200,
            5: 57_600,
            6: 38_400,
            7: 19_200,
        }

        for test_baudrate in feetech_baudrates:
            port_handler = scs.PortHandler(port)
            packet_handler = scs.PacketHandler(0)

            if not port_handler.openPort():
                continue

            port_handler.setBaudRate(test_baudrate)

            model_number, comm, error = packet_handler.ping(
                port_handler, motor_id
            )

            if comm == scs.COMM_SUCCESS and error == 0:
                print(f"✓ Motor found at {test_baudrate} baud!")

                # Find model name
                model_name = "Unknown"
                for name, num in MODEL_NUMBER_TABLE.items():
                    if num == model_number:
                        model_name = name
                        break

                print(f"Model: {model_name} (#{model_number})")

                # Read various registers
                try:
                    # Baudrate
                    baud_val, _, _ = packet_handler.read1ByteTxRx(
                        port_handler, motor_id, 6
                    )
                    configured_baud = baudrate_values.get(baud_val, "Unknown")
                    print(
                        f"Configured baudrate: {configured_baud} (register value: {baud_val})"
                    )

                    # ID
                    id_val, _, _ = packet_handler.read1ByteTxRx(
                        port_handler, motor_id, 5
                    )
                    print(f"Motor ID: {id_val}")

                    # Firmware version
                    fw_major, _, _ = packet_handler.read1ByteTxRx(
                        port_handler, motor_id, 0
                    )
                    fw_minor, _, _ = packet_handler.read1ByteTxRx(
                        port_handler, motor_id, 1
                    )
                    print(f"Firmware version: {fw_major}.{fw_minor}")

                    # Position limits
                    min_pos, _, _ = packet_handler.read2ByteTxRx(
                        port_handler, motor_id, 9
                    )
                    max_pos, _, _ = packet_handler.read2ByteTxRx(
                        port_handler, motor_id, 11
                    )
                    print(f"Position limits: {min_pos} - {max_pos}")

                    # Current position
                    curr_pos, _, _ = packet_handler.read2ByteTxRx(
                        port_handler, motor_id, 56
                    )
                    print(f"Current position: {curr_pos}")

                    # Torque enable
                    torque, _, _ = packet_handler.read1ByteTxRx(
                        port_handler, motor_id, 40
                    )
                    print(f"Torque enabled: {'Yes' if torque else 'No'}")

                except Exception as e:
                    print(f"Error reading motor registers: {e}")

                port_handler.closePort()
                return True

            port_handler.closePort()

        print("Motor not found at any baudrate")
        return False

    except ImportError:
        print("Error: scservo_sdk not installed. Please install it with:")
        print("pip install scservo_sdk")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


# Add the new functions to the existing script
if __name__ == "__main__":
    # comprehensive_port_check()

    # Example usage of Feetech-specific functions
    print("\n" + "=" * 70)
    print("FEETECH MOTOR SPECIFIC CHECKS")
    print("=" * 70)

    # Replace with your actual port
    test_port = "/dev/tty.usbserial-0001"  # Update this to your actual port

    # Uncomment and modify these lines to test with your setup:
    print("\n" + "=" * 70)
    scan_feetech_bus(test_port)
    print("\n" + "=" * 70)
    check_feetech_motor_baudrate(test_port, motor_id=1)
    print("\n" + "=" * 70)
    check_feetech_motor_detailed(test_port, motor_id=1)