import time
import xtralien
import datetime
from decimal import Decimal
import logging
from enum import Enum


class I_range_mode(int,Enum):
    """Current range modes for the potentiostat.
    
    Attributes:
        MILLIAMPS200: 200 milliamps range
        MILLIAMPS20: 20 milliamps range
        MICROAMPS2000: 2000 microamps range
        MICROAMPS200: 200 microamps range
        MICROAMPS20: 20 microamps range
    """
    MILLIAMPS200 = 1
    MILLIAMPS20 = 2
    MICROAMPS2000 = 3
    MICROAMPS200 = 4
    MICROAMPS20 = 5


class Potentiostat:
    """Interface for controlling a potentiostat device via xtralien.
    
    This class provides methods for various electrochemical measurements including
    cyclic voltammetry, linear voltammetry, open circuit measurements, and electrolysis.
    """
    
    def __init__(
        self,
        com_port,
        save_file_location,
        smu_channel="smu1",
        vsense_channel="vsense1",
        logger = logging.getLogger(__name__)
    ):
        """Initialize the Potentiostat.
        
        Args:
            com_port: COM port for device connection (e.g., "/dev/ttyACM0" or "COM3")
            save_file_location: Directory path where CSV output files will be saved
            smu_channel: Source measure unit channel name (default: "smu1")
            vsense_channel: Voltage sense channel name (default: "vsense1")
        """
        self.com_port = com_port
        self._device = xtralien.Device(self.com_port)
        self.smu_channel = smu_channel
        self.vsense_channel = vsense_channel
        self.save_file_location = save_file_location
        self._sleep_time = 0.05
        self.logger = logger

        self.logger.info("setting Vsense Settings")
        self.logger.debug("setting Vsense to enabled")
        self._device[self.vsense_channel].set.enabled(True, response=0)
        time.sleep(self._sleep_time)
        self.logger.debug("Setting vsense OSR to 6")
        self._device[self.vsense_channel].set.osr(6, response=0)
        time.sleep(self._sleep_time)

        self.logger.info("setting SMU Settings")
        self.logger.debug("setting SMU OSR to 6")
        self._device[self.smu_channel].set.osr(6, response=0)
        time.sleep(self._sleep_time)

    def get_status(self) -> bool:
        """Get the error status of the potentiostat.
        
        Returns:
            bool: Error status from the SMU channel
        """
        self.logger.debug("Getting Error Status")
        error_status = self._device[self.smu_channel].get.error()[:-1]
        self.logger.debug(f"Error status: {error_status}")
        return error_status

    def cyclic_voltemmetry(
        self,
        i_range: I_range_mode,
        start_potential: Decimal,
        potential_vertex: Decimal,
        scan_rate: float,
        cycles: int,
        increment=Decimal(0.01),
    ) -> str:
        """Perform cyclic voltammetry measurement.
        
        Sweeps the potential from start_potential to potential_vertex and back,
        repeating for the specified number of cycles. Data is saved to a CSV file.
        
        Args:
            i_range: Current range setting for the measurement
            start_potential: Starting potential in volts
            potential_vertex: Maximum potential to reach before reversing in volts
            scan_rate: Rate of potential change in V/s
            cycles: Number of forward-reverse cycles to perform
            increment: Potential step size in volts (default: 0.01)
            
        Returns:
            str: Path to the saved CSV file containing voltage and current data
        """
        self.logger.debug(f"Setting SMU range to {i_range}")
        self._device[self.smu_channel].set.range(i_range, response=0)
        time.sleep(self._sleep_time)

        self.logger.debug("Setting SMU channel enabled")
        self._device[self.smu_channel].set.enabled(True, response=0)
        time.sleep(self._sleep_time)

        set_v = start_potential
        for cycle in range(1, cycles + 1):
            self.logger.info(f"Starting cycle {cycle}")
            with open(
                self.save_file_location + "cyclic_voltemmetry" + ".csv", "w+"
            ) as f:
                f.write("Potential,Current\n")
                # go up
                while set_v <= potential_vertex:
                    # set voltage and read
                    try:
                        
                        voltage, current = self._device[self.smu_channel].oneshot(set_v)[0]
                    except Exception as e:
                        self.logger.error(f"Could oneshot error: {e}")
                        self.logger.error("shutting down SMU")
                        self.logger.info("setting voltage to 0")
                        self._device[self.smu_channel].set.voltage(0, response=0)
                        time.sleep(self._sleep_time)
                        
                        self._device[self.smu_channel].set.enabled(False, response=0)
                        time.sleep(self._sleep_time)
                        raise e
                     
                    self.logger.debug(f"Voltage: {voltage}, Current: {current}")
                    f.write(f"{voltage},{current}\n")

                    
                    set_v += increment
                    # wait the appropriate time per increment to get the correct scanrate
                    time.sleep(float(increment) / scan_rate)
                # go down
                while set_v >= start_potential:
                    voltage, current = self._device[self.smu_channel].oneshot(set_v)[0]
                    f.write(f"{voltage},{current}\n")
                    self.logger.debug(f"Voltage: {voltage}, Current: {current}")
                    set_v -= increment
                    time.sleep(float(increment) / scan_rate)

        # clean up
        self.logger.debug("setting voltage to 0")
        self._device[self.smu_channel].set.voltage(0, response=0)
        time.sleep(self._sleep_time)
        
        self._device[self.smu_channel].set.enabled(False, response=0)
        time.sleep(self._sleep_time)
        
        return self.save_file_location + "cyclic_voltemmetry" + ".csv"

    def linear_voltemmetry(
        self,
        i_range: I_range_mode,
        start_potential: Decimal,
        end_potential: Decimal,
        scan_rate: float,
        increment=Decimal(0.01),
    ) -> str:
        """Perform linear sweep voltammetry measurement.
        
        Sweeps the potential linearly from start_potential to end_potential
        while measuring current. Data is saved to a CSV file.
        
        Args:
            i_range: Current range setting for the measurement
            start_potential: Starting potential in volts
            end_potential: Final potential in volts
            scan_rate: Rate of potential change in V/s
            increment: Potential step size in volts (default: 0.01)
            
        Returns:
            str: Path to the saved CSV file containing voltage and current data
        """
        self.logger.debug(f"Setting SMU range to {i_range}")
        self._device[self.smu_channel].set.range(i_range, response=0)
        time.sleep(self._sleep_time)

        self.logger.debug("Setting SMU channel enabled")
        self._device[self.smu_channel].set.enabled(True, response=0)
        time.sleep(self._sleep_time)

        set_v = start_potential
        with open(self.save_file_location + "linear_voltemetry" + ".csv", "w+") as f:
            f.write("Potential,Current\n")
            # go up
            while set_v <= end_potential:
                # set voltage and read
                try:
                    voltage, current = self._device[self.smu_channel].oneshot(set_v)[0]
                except Exception as e:
                    self.logger.error(f"Could oneshot error: {e}")
                    self.logger.error("shutting down SMU")
                    self.logger.info("setting voltage to 0")
                    self._device[self.smu_channel].set.voltage(0, response=0)
                    time.sleep(self._sleep_time)
                    
                    self._device[self.smu_channel].set.enabled(False, response=0)
                    time.sleep(self._sleep_time)
                    raise e
                    
                self.logger.debug(f"Voltage: {voltage},Current: {current}")
                f.write(f"{voltage},{current}\n")

                set_v += increment
                # wait the appropriate time per increment to get the correct scanrate
                self.logger.debug(f"waiting for {float(increment) / scan_rate}")
                time.sleep(float(increment) / scan_rate)
        # clean up
        self.logger.info("setting voltage to 0")
        self._device[self.smu_channel].set.voltage(0, response=0)
        time.sleep(self._sleep_time)
        
        self.logger.info("setting SMU disabled")
        self._device[self.smu_channel].set.enabled(False, response=0)
        time.sleep(self._sleep_time)
        
        return self.save_file_location + "linear_voltemetry" + ".csv"

    def open_circuit(self, duration: float, sampling_period: float) -> str:
        """Measure open circuit potential over time.
        
        Records the voltage at the vsense channel without applying current,
        measuring the natural potential of the system. Data is saved to a CSV file.
        
        Args:
            duration: Total measurement time in seconds
            sampling_period: Time between measurements in seconds
            
        Returns:
            str: Path to the saved CSV file containing time and voltage data
        """
        with open(self.save_file_location + "open_circuit" + ".csv", "w+") as f:
            f.write("Seconds,Voltage\n")
            startime = datetime.datetime.now()
            how_long = 0
            while how_long < duration:
                how_long = (datetime.datetime.now() - startime).total_seconds()
                voltage = self._device[self.vsense_channel].measure()[0]
                self.logger.debug(f"seconds: {how_long},Voltage: {voltage}")
                f.write(f"{how_long},{voltage}\n")
                time.sleep(sampling_period)
        return self.save_file_location + "open_circuit" + ".csv"

    def electrolysis(
        self,
        i_range: I_range_mode,
        potential: Decimal,
        duration: float,
        sampling_period: float,
    ) -> str:
        """Perform constant potential electrolysis.
        
        Applies a constant potential and measures the current over time.
        Data is saved to a CSV file.
        
        Args:
            i_range: Current range setting for the measurement
            potential: Constant potential to apply in volts
            duration: Total measurement time in seconds
            sampling_period: Time between current measurements in seconds
            
        Returns:
            str: Path to the saved CSV file containing time and current data
        """
        self.logger.debug(f"Setting range to {i_range}")
        self._device[self.smu_channel].set.range(i_range, response=0)
        time.sleep(self._sleep_time)

        self.logger.debug("Setting SMU to Enabled")
        self._device[self.smu_channel].set.enabled(True, response=0)
        time.sleep(self._sleep_time)

        self.logger.info(f"setting_voltage to {potential}")
        self._device[self.smu_channel].set.voltage(potential, response=0)
        time.sleep(self._sleep_time)
        
        with open(self.save_file_location + "electrolysis" + ".csv", "w+") as f:
            f.write("Seconds,Current\n")
            startime = datetime.datetime.now()
            how_long = 0
            while how_long < duration:
                how_long = (datetime.datetime.now() - startime).total_seconds()
                current = self._device[self.smu_channel].measurei()[0]
                f.write(f"{how_long},{current}\n")
                time.sleep(sampling_period)
        return self.save_file_location + "electrolysis" + ".csv"

    def _shutdown(self):
        """Safely shut down the potentiostat.
        
        Sets voltage to 0, disables the SMU channel, and closes the device connection.
        This is a private method for internal cleanup.
        """
        self.logger.info("setting voltage to 0")
        self._device[self.smu_channel].set.voltage(0, response=0)
        time.sleep(self._sleep_time)
        
        self.logger.info("Setting SMU to disabled")
        self._device[self.smu_channel].set.enabled(False, response=0)
        time.sleep(self._sleep_time)

        self._device.close()
