"""
Core meter classes for ham radio station measurements
"""

import time
import random
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class BaseMeter(ABC):
    """Base class for all meter types"""
    
    def __init__(self, name: str, unit: str):
        """
        Initialize a meter
        
        Args:
            name: Name of the meter
            unit: Unit of measurement (e.g., 'W', 'dB', 'V')
        """
        self.name = name
        self.unit = unit
        self._value = 0.0
        self._timestamp = None
        
    @abstractmethod
    def read(self) -> float:
        """
        Read the current value from the meter
        
        Returns:
            Current measurement value
        """
        pass
    
    def get_reading(self) -> Dict[str, Any]:
        """
        Get a complete reading with metadata
        
        Returns:
            Dictionary containing value, unit, timestamp, and meter name
        """
        value = self.read()
        return {
            'name': self.name,
            'value': value,
            'unit': self.unit,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    @property
    def value(self) -> float:
        """Get the last read value"""
        return self._value


class PowerMeter(BaseMeter):
    """Power meter for measuring RF output power"""
    
    def __init__(self, name: str = "Power", max_power: float = 100.0):
        """
        Initialize a power meter
        
        Args:
            name: Name of the meter
            max_power: Maximum power in watts
        """
        super().__init__(name, "W")
        self.max_power = max_power
        self._simulate = True
        
    def read(self) -> float:
        """
        Read power value
        
        Returns:
            Power in watts
        """
        if self._simulate:
            # Simulate power reading with some variation
            self._value = random.uniform(0, self.max_power)
        
        self._timestamp = time.time()
        return self._value
    
    def set_value(self, value: float):
        """
        Manually set the power value (for hardware integration)
        
        Args:
            value: Power value in watts
        """
        self._simulate = False
        self._value = min(max(0, value), self.max_power)
        self._timestamp = time.time()


class SWRMeter(BaseMeter):
    """SWR (Standing Wave Ratio) meter for antenna efficiency"""
    
    def __init__(self, name: str = "SWR"):
        """
        Initialize an SWR meter
        
        Args:
            name: Name of the meter
        """
        super().__init__(name, ":1")
        self._simulate = True
        
    def read(self) -> float:
        """
        Read SWR value
        
        Returns:
            SWR ratio (typically 1.0 to 3.0)
        """
        if self._simulate:
            # Simulate SWR reading (1.0 is perfect, higher is worse)
            self._value = random.uniform(1.0, 2.0)
        
        self._timestamp = time.time()
        return self._value
    
    def set_value(self, value: float):
        """
        Manually set the SWR value (for hardware integration)
        
        Args:
            value: SWR ratio
        """
        self._simulate = False
        self._value = max(1.0, value)
        self._timestamp = time.time()


class SignalStrengthMeter(BaseMeter):
    """Signal strength meter (S-meter)"""
    
    def __init__(self, name: str = "Signal Strength"):
        """
        Initialize a signal strength meter
        
        Args:
            name: Name of the meter
        """
        super().__init__(name, "dB")
        self._simulate = True
        
    def read(self) -> float:
        """
        Read signal strength
        
        Returns:
            Signal strength in dB
        """
        if self._simulate:
            # Simulate signal strength (-120 to 0 dB)
            self._value = random.uniform(-120, -20)
        
        self._timestamp = time.time()
        return self._value
    
    def set_value(self, value: float):
        """
        Manually set the signal strength (for hardware integration)
        
        Args:
            value: Signal strength in dB
        """
        self._simulate = False
        self._value = value
        self._timestamp = time.time()


class VoltageMeter(BaseMeter):
    """Voltage meter for monitoring power supply"""
    
    def __init__(self, name: str = "Voltage", max_voltage: float = 15.0):
        """
        Initialize a voltage meter
        
        Args:
            name: Name of the meter
            max_voltage: Maximum voltage to measure
        """
        super().__init__(name, "V")
        self.max_voltage = max_voltage
        self._simulate = True
        
    def read(self) -> float:
        """
        Read voltage value
        
        Returns:
            Voltage in volts
        """
        if self._simulate:
            # Simulate voltage reading around 13.8V (typical for ham radio)
            self._value = random.uniform(12.5, 14.2)
        
        self._timestamp = time.time()
        return self._value
    
    def set_value(self, value: float):
        """
        Manually set the voltage value (for hardware integration)
        
        Args:
            value: Voltage in volts
        """
        self._simulate = False
        self._value = min(max(0, value), self.max_voltage)
        self._timestamp = time.time()
