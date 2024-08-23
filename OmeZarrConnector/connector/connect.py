import cv2
import numpy as np
import zarr
import dask.array as da
import os 
import math
import xml.etree.ElementTree as ET

class OmeZarrConnector: 
  """
  Connector for ome zarr files
  """
  def __init__(self, path):
    """
    Initialize the connector

    Args:
    path: path to the ome zarr file
    """
    self.path = path # Path to the ome zarr file
    self.metadata = [] # Metadata for the ome zarr file
    self.full_size_x = 0 # Full shape of the image in x direction
    self.full_size_y = 0
    self.zarr_connection = zarr.open(self.path) # Open the zarr file
    self.total_zoom_levels = len(self.zarr_connection[0]) # Total zoom levels in the main image zarr file
    self.dzi_total_zoom_levels = 0 # Total zoom levels in the dzi file
    self.tile_size = 256 # Tile size square
    self.largest_zoom_level_with_full_tile = 0
    self.color_map = {
      'red': [1, 0, 0],
      'green': [0, 1, 0],
      'blue': [0, 0, 1],
      'yellow': [1, 1, 0],
      'magenta': [1, 0, 1],
      'cyan': [0, 1, 1],
      'white': [1, 1, 1]
    }
  
    self.get_metadata()
    self.calculate_largest_zoom_level_with_full_tile()
    self.calculate_dzi_total_zoom_levels()


  def calculate_dzi_total_zoom_levels(self) -> None:
    """
    Calculate the total number of zoom levels for DZI pyramid,
    continuing until the image is scaled down to less than 1 pixel
    in either dimension.
    """
    # Ensure full_size_x and full_size_y are initialized
    if self.full_size_x <= 0 or self.full_size_y <= 0:
        raise ValueError("Full size dimensions must be positive numbers")

    # Get the largest dimension
    max_dimension = max(self.full_size_x, self.full_size_y)

    # Calculate the number of times we need to divide by 2 to get below 1
    self.dzi_total_zoom_levels = math.ceil(math.log2(max_dimension))
  
  def calculate_largest_zoom_level_with_full_tile(self) -> None:
    # Calculate how many times we can halve x and y before they become smaller than tile size
    max_zoom_x = math.floor(math.log2(self.full_size_x / self.tile_size))
    max_zoom_y = math.floor(math.log2(self.full_size_y / self.tile_size))
    
    # Return the smaller of the two values
    self.largest_zoom_level_with_full_tile = min(max_zoom_x, max_zoom_y)

  def return_metadata(self) -> dict:
    """
    Return metadata for the ome zarr file
    """
    return self.metadata

  def get_metadata(self) -> None:
    """
    Get metadata for the ome zarr file
    """
    tree = ET.parse(os.path.join(self.path, 'OME', 'METADATA.ome.xml'))
    root = tree.getroot()

    namespace = {'ome': 'http://www.openmicroscopy.org/Schemas/OME/2016-06'}
    self.metadata = []
    # Get image metadata
    for image in root.findall('ome:Image', namespace):
      image_id = image.get('ID')
      image_name = image.get('Name')

      # Get image details
      pixel_info = []
      pixels = image.find('ome:Pixels', namespace)
      if pixels is not None:
        size_x = pixels.get('SizeX')
        size_y = pixels.get('SizeY')
        size_c = pixels.get('SizeC')
        physical_size_x = pixels.get('PhysicalSizeX')
        physical_size_x_unit = pixels.get('PhysicalSizeXUnit')
        physical_size_y = pixels.get('PhysicalSizeY')
        physical_size_y_unit = pixels.get('PhysicalSizeYUnit')
        pixel_info.append({
            'size_x': size_x,
            'size_y': size_y,
            'size_c': size_c,
            'physical_size_x': physical_size_x,
            'physical_size_x_unit': physical_size_x_unit,
            'physical_size_y': physical_size_y,
            'physical_size_y_unit': physical_size_y_unit
            })
        
      self.metadata.append({
          'image_id': image_id,
          'image_name': image_name,
          'pixel_info': pixel_info
          })
    
    self.full_size_x = int(self.metadata[0]['pixel_info'][0]['size_x']) # assuming first image is the main image
    self.full_size_y = int(self.metadata[0]['pixel_info'][0]['size_y']) # assuming first image is the main image
  
  def return_color_map(self) -> dict: 
    """
    Return the color map
    """
    return self.color_map
  
  def generate_dzi(self, image_id) -> str:
    """
    Generate dzi text for the ome zarr file

    Args:
      image_id: image id (the sequential number) for which dzi file needs to be generated

    """
    # Get image size
    size_x = self.metadata[image_id]['pixel_info'][0]['size_x']
    size_y = self.metadata[image_id]['pixel_info'][0]['size_y']
    # Generate dzi

    dzi = '<?xml version="1.0" encoding="UTF-8"?>\n'
    dzi += f'<Image TileSize="256" Overlap="0" Format="png" xmlns="http://schemas.microsoft.com/deepzoom/2008">\n'
    dzi += f'  <Size Width="{size_x}" Height="{size_y}"/>\n'
    dzi += '</Image>\n'

    return dzi
  
  def get_tile_image(self, image_id, zoom_level, channel, tile_x, tile_y) -> np.array:
    """
    Get a tile from the ome zarr file, with support for DZI zoom levels

    Args:
      image_id: image id (the sequential number) for which tile needs to be extracted
      zoom_level: zoom level (DZI format, where higher numbers mean more zoomed out)
      channel: channel to be extracted
      tile_x: x coordinate of the tile
      tile_y: y coordinate of the tile
    """
    root = zarr.open('/Users/vanijzen/Desktop/example-raw.zarr')[image_id]
    
    # Determine the zarr zoom level
    zarr_zoom_level = min(zoom_level, self.largest_zoom_level_with_full_tile)
    da_zarr = da.from_zarr(root[zarr_zoom_level])

    full_width = da_zarr.shape[4]
    full_height = da_zarr.shape[3]
    
    # Calculate the region of the image to extract
    tile_size = self.tile_size  # Assuming square tiles
    start_x = tile_x * tile_size 
    start_y = tile_y * tile_size
    end_x = min(start_x + tile_size, full_width)
    end_y = min(start_y + tile_size, full_height)
    
    # Extract the region from the Dask array
    if zoom_level < self.largest_zoom_level_with_full_tile:
      region = da_zarr[0, channel, 0, start_y:end_y, start_x:end_x].compute()

    # If we're at a deeper zoom level than the zarr file provides, we need to scale
    else:
      scale_factor = 2 ** (zoom_level - self.largest_zoom_level_with_full_tile)
      level_width = full_width // scale_factor
      level_height = full_height // scale_factor
      
      # Calculate the region of the image to extract
      start_x = tile_x * self.tile_size
      start_y = tile_y * self.tile_size
      end_x = min(start_x + self.tile_size, level_width)
      end_y = min(start_y + self.tile_size, level_height)
      
      # Calculate the region in the original image coordinates
      orig_start_x = start_x * scale_factor
      orig_start_y = start_y * scale_factor
      orig_end_x = end_x * scale_factor
      orig_end_y = end_y * scale_factor
      
      # Extract the region from the Dask array
      region = da_zarr[0, channel, 0, orig_start_y:orig_end_y, orig_start_x:orig_end_x].compute()

      new_width = end_x - start_x
      new_height = end_y - start_y

      try:
        region = cv2.resize(region, (new_width, new_height), interpolation=cv2.INTER_AREA)
      except: 
        region = np.array([1])

    return region
  
  def get_combined_image(self, image_id, dzi_zoom_level, channels, intensities, colors, tile_x, tile_y) -> np.array:
    """
    Get a combined image from the ome zarr file

    Args:
      image_id: image id (the sequential number) for which tile needs to be extracted
      dzi_zoom_level: zoom level
      channels: list of channels to be extracted
      intensities: list of intensities for each channel
      colors: list of colors for each channel
      tile_x: x coordinate of the tile
      tile_y: y coordinate of the tile
    """

    # Get the zoom level for the zarr file
    zoom_level = self.dzi_total_zoom_levels - dzi_zoom_level - 1

    merged_image = None #np.zeros((self.tile_size, self.tile_size, 3), dtype=np.uint8)
    
    for channel, intensity, color in zip(channels, intensities, colors):
      color_rgb = self.color_map[color]
      image = self.get_tile_image(image_id, zoom_level, channel, tile_x, tile_y)
      enhanced_image = cv2.convertScaleAbs(image, alpha=intensity)
      colored_image = cv2.merge([enhanced_image * color_rgb[i] for i in range(3)])
      if merged_image is None:
        merged_image = colored_image
      merged_image = cv2.add(merged_image, colored_image)
    
    return merged_image