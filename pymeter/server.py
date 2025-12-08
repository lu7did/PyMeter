"""
Server implementation for remote meter access
"""

import socket
import json
import threading
import logging
from typing import List, Dict, Any
from .meters import BaseMeter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MeterServer:
    """TCP server for remote meter access"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5555):
        """
        Initialize the meter server
        
        Args:
            host: Host address to bind to
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.meters: Dict[str, BaseMeter] = {}
        self.running = False
        self.server_socket = None
        self.clients = []
        
    def add_meter(self, meter: BaseMeter):
        """
        Add a meter to the server
        
        Args:
            meter: Meter instance to add
        """
        self.meters[meter.name] = meter
        logger.info(f"Added meter: {meter.name}")
        
    def remove_meter(self, name: str):
        """
        Remove a meter from the server
        
        Args:
            name: Name of the meter to remove
        """
        if name in self.meters:
            del self.meters[name]
            logger.info(f"Removed meter: {name}")
            
    def get_all_readings(self) -> Dict[str, Any]:
        """
        Get readings from all meters
        
        Returns:
            Dictionary of meter readings
        """
        readings = {}
        for name, meter in self.meters.items():
            readings[name] = meter.get_reading()
        return readings
    
    def get_reading(self, meter_name: str) -> Dict[str, Any]:
        """
        Get reading from a specific meter
        
        Args:
            meter_name: Name of the meter
            
        Returns:
            Dictionary containing the meter reading
        """
        if meter_name in self.meters:
            return self.meters[meter_name].get_reading()
        return {'error': f'Meter {meter_name} not found'}
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """
        Handle client connection
        
        Args:
            client_socket: Client socket
            address: Client address
        """
        logger.info(f"Client connected from {address}")
        
        try:
            while self.running:
                try:
                    # Receive command from client
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                        
                    command = json.loads(data)
                    response = self.process_command(command)
                    
                    # Send response
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError:
                    error_response = {'error': 'Invalid JSON'}
                    client_socket.send(json.dumps(error_response).encode('utf-8'))
                except Exception as e:
                    logger.error(f"Error handling client: {e}")
                    break
                    
        finally:
            client_socket.close()
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            logger.info(f"Client disconnected from {address}")
    
    def process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a command from a client
        
        Args:
            command: Command dictionary
            
        Returns:
            Response dictionary
        """
        cmd_type = command.get('command', '')
        
        if cmd_type == 'get_all':
            return {
                'status': 'success',
                'data': self.get_all_readings()
            }
        elif cmd_type == 'get_meter':
            meter_name = command.get('meter', '')
            return {
                'status': 'success',
                'data': self.get_reading(meter_name)
            }
        elif cmd_type == 'list_meters':
            return {
                'status': 'success',
                'data': {
                    'meters': [
                        {
                            'name': meter.name,
                            'unit': meter.unit
                        }
                        for meter in self.meters.values()
                    ]
                }
            }
        else:
            return {
                'status': 'error',
                'message': f'Unknown command: {cmd_type}'
            }
    
    def start(self):
        """Start the meter server"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            logger.info(f"Meter server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, address = self.server_socket.accept()
                    self.clients.append(client_socket)
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
                        
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            # Cleanup without calling stop() to avoid potential recursion
            self.running = False
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
    
    def stop(self):
        """Stop the meter server"""
        self.running = False
        
        # Close all client connections
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            
        logger.info("Meter server stopped")
