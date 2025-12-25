"""
XMP Metadata Export für PNG und TIFF

Implementiert XMP (Extensible Metadata Platform) Support für PNG und TIFF Formate.
Erweitert matplotlib's savefig mit vollständigen Metadaten nach FAIR-Prinzipien.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional
import xml.etree.ElementTree as ET


def create_xmp_packet(metadata: Dict[str, str]) -> str:
    """
    Erstellt ein XMP-Metadaten-Paket im XML-Format.

    XMP (Adobe's Extensible Metadata Platform) ist der Standard für
    Metadaten in Bilddateien und wird von den meisten Bildbetrachterprogrammen
    und Betriebssystemen (Windows Explorer, macOS Finder, etc.) unterstützt.

    Args:
        metadata: Dictionary mit Metadaten

    Returns:
        str: XMP-XML als String
    """
    # XMP Namespaces
    namespaces = {
        'x': 'adobe:ns:meta/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'xmp': 'http://ns.adobe.com/xap/1.0/',
        'xmpRights': 'http://ns.adobe.com/xap/1.0/rights/',
        'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
        'cc': 'http://creativecommons.org/ns#',
        # Custom namespace für wissenschaftliche Metadaten
        'scatterforge': 'http://scatterforge.org/ns/1.0/'
    }

    # XML mit proper formatting
    xmp_lines = [
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>',
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">',
        '  <rdf:RDF'
    ]

    # Namespace declarations
    for prefix, uri in namespaces.items():
        xmp_lines.append(f'    xmlns:{prefix}="{uri}"')

    xmp_lines.append('  >')
    xmp_lines.append('    <rdf:Description rdf:about="">')

    # Dublin Core (dc:) - Standard Metadaten
    if metadata.get('Title'):
        xmp_lines.append(f'      <dc:title>{_escape_xml(metadata["Title"])}</dc:title>')

    if metadata.get('Author'):
        xmp_lines.append('      <dc:creator>')
        xmp_lines.append('        <rdf:Seq>')
        xmp_lines.append(f'          <rdf:li>{_escape_xml(metadata["Author"])}</rdf:li>')
        xmp_lines.append('        </rdf:Seq>')
        xmp_lines.append('      </dc:creator>')

    if metadata.get('Subject'):
        xmp_lines.append(f'      <dc:description>{_escape_xml(metadata["Subject"])}</dc:description>')

    if metadata.get('Keywords'):
        keywords = [k.strip() for k in metadata['Keywords'].split(',') if k.strip()]
        if keywords:
            xmp_lines.append('      <dc:subject>')
            xmp_lines.append('        <rdf:Bag>')
            for keyword in keywords:
                xmp_lines.append(f'          <rdf:li>{_escape_xml(keyword)}</rdf:li>')
            xmp_lines.append('        </rdf:Bag>')
            xmp_lines.append('      </dc:subject>')

    # XMP Basic (xmp:)
    if metadata.get('CreationDate'):
        xmp_lines.append(f'      <xmp:CreateDate>{metadata["CreationDate"]}</xmp:CreateDate>')
        xmp_lines.append(f'      <xmp:MetadataDate>{metadata["CreationDate"]}</xmp:MetadataDate>')

    if metadata.get('Creator_Tool'):
        xmp_lines.append(f'      <xmp:CreatorTool>{_escape_xml(metadata["Creator_Tool"])}</xmp:CreatorTool>')

    # Rights Management (xmpRights:)
    if metadata.get('License'):
        xmp_lines.append(f'      <xmpRights:UsageTerms>{_escape_xml(metadata["License"])}</xmpRights:UsageTerms>')

    if metadata.get('License_URL'):
        xmp_lines.append(f'      <xmpRights:WebStatement>{metadata["License_URL"]}</xmpRights:WebStatement>')

    # Photoshop (für Affiliation/Author Position)
    if metadata.get('Affiliation'):
        xmp_lines.append(f'      <photoshop:AuthorsPosition>{_escape_xml(metadata["Affiliation"])}</photoshop:AuthorsPosition>')

    # Creative Commons (falls CC-Lizenz)
    if metadata.get('License_URL') and 'creativecommons.org' in metadata.get('License_URL', ''):
        xmp_lines.append(f'      <cc:license>{metadata["License_URL"]}</cc:license>')

    # Custom ScatterForge Namespace für wissenschaftliche Metadaten
    if metadata.get('Creator_ORCID'):
        xmp_lines.append(f'      <scatterforge:CreatorORCID>{metadata["Creator_ORCID"]}</scatterforge:CreatorORCID>')

    if metadata.get('Affiliation_ROR'):
        xmp_lines.append(f'      <scatterforge:AffiliationROR>{metadata["Affiliation_ROR"]}</scatterforge:AffiliationROR>')

    if metadata.get('Creator_Tool_Version'):
        xmp_lines.append(f'      <scatterforge:SoftwareVersion>{metadata["Creator_Tool_Version"]}</scatterforge:SoftwareVersion>')

    if metadata.get('Python_Version'):
        xmp_lines.append(f'      <scatterforge:PythonVersion>{metadata["Python_Version"]}</scatterforge:PythonVersion>')

    if metadata.get('Matplotlib_Version'):
        xmp_lines.append(f'      <scatterforge:MatplotlibVersion>{metadata["Matplotlib_Version"]}</scatterforge:MatplotlibVersion>')

    if metadata.get('Image_UUID'):
        xmp_lines.append(f'      <scatterforge:ImageUUID>{metadata["Image_UUID"]}</scatterforge:ImageUUID>')

    if metadata.get('CreationDate_Unix'):
        xmp_lines.append(f'      <scatterforge:CreationDateUnix>{metadata["CreationDate_Unix"]}</scatterforge:CreationDateUnix>')

    # Experiment metadata (optional)
    if metadata.get('Experiment_ID'):
        xmp_lines.append(f'      <scatterforge:ExperimentID>{_escape_xml(metadata["Experiment_ID"])}</scatterforge:ExperimentID>')

    if metadata.get('Measurement_Date'):
        xmp_lines.append(f'      <scatterforge:MeasurementDate>{metadata["Measurement_Date"]}</scatterforge:MeasurementDate>')

    if metadata.get('Sample_ID'):
        xmp_lines.append(f'      <scatterforge:SampleID>{_escape_xml(metadata["Sample_ID"])}</scatterforge:SampleID>')

    # Close tags
    xmp_lines.append('    </rdf:Description>')
    xmp_lines.append('  </rdf:RDF>')
    xmp_lines.append('</x:xmpmeta>')
    xmp_lines.append('<?xpacket end="w"?>')

    return '\n'.join(xmp_lines)


def _escape_xml(text: str) -> str:
    """
    Escaped XML-Sonderzeichen.

    Args:
        text: Text zum Escapen

    Returns:
        str: Escaped Text
    """
    if not text:
        return ''

    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text


def embed_xmp_metadata_png(image_path: Path, metadata: Dict[str, str]) -> bool:
    """
    Bettet XMP-Metadaten in eine PNG-Datei ein.

    PNG speichert XMP in einem iTXt-Chunk mit dem Keyword "XML:com.adobe.xmp".

    Args:
        image_path: Pfad zur PNG-Datei
        metadata: Dictionary mit Metadaten

    Returns:
        bool: True bei Erfolg

    Raises:
        ImportError: Wenn PIL nicht verfügbar ist
        IOError: Bei Dateizugriffsfehler
    """
    try:
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo
    except ImportError:
        raise ImportError("PIL (Pillow) wird benötigt für XMP-Support in PNG")

    # XMP-Paket erstellen
    xmp_packet = create_xmp_packet(metadata)

    # Bild öffnen
    img = Image.open(image_path)

    # PNG Info mit XMP erstellen
    pnginfo = PngInfo()

    # XMP als iTXt chunk hinzufügen
    pnginfo.add_itxt("XML:com.adobe.xmp", xmp_packet)

    # Bild mit Metadaten überschreiben
    img.save(image_path, pnginfo=pnginfo)

    return True


def embed_xmp_metadata_tiff(image_path: Path, metadata: Dict[str, str]) -> bool:
    """
    Bettet XMP-Metadaten in eine TIFF-Datei ein.

    TIFF speichert XMP im TIFF-Tag 700 (XMP).

    Args:
        image_path: Pfad zur TIFF-Datei
        metadata: Dictionary mit Metadaten

    Returns:
        bool: True bei Erfolg

    Raises:
        ImportError: Wenn PIL nicht verfügbar ist
        IOError: Bei Dateizugriffsfehler
    """
    try:
        from PIL import Image
        from PIL.TiffImagePlugin import ImageFileDirectory_v2
    except ImportError:
        raise ImportError("PIL (Pillow) wird benötigt für XMP-Support in TIFF")

    # XMP-Paket erstellen
    xmp_packet = create_xmp_packet(metadata)

    # Bild öffnen
    img = Image.open(image_path)

    # TIFF Tag 700 für XMP setzen
    # Note: PIL/Pillow unterstützt das direkte Setzen von Tag 700
    # Wir nutzen save() mit tiffinfo parameter

    # TiffImagePlugin kann direkt mit XMP umgehen
    # XMP wird automatisch als Bytes gespeichert
    xmp_bytes = xmp_packet.encode('utf-8')

    # TIFF speichern mit XMP
    img.save(
        image_path,
        format='TIFF',
        tiffinfo={700: xmp_bytes}  # Tag 700 = XMP
    )

    return True


def add_metadata_to_export(file_path: Path, metadata: Dict[str, str], format: str) -> bool:
    """
    Fügt Metadaten zu einer exportierten Datei hinzu.

    Args:
        file_path: Pfad zur Exportdatei
        metadata: Dictionary mit Metadaten
        format: Dateiformat ('PNG', 'TIFF', 'SVG', 'PDF', 'EPS')

    Returns:
        bool: True bei Erfolg, False wenn Format nicht unterstützt

    Raises:
        ImportError: Wenn benötigte Libraries fehlen
        IOError: Bei Dateizugriffsfehler
    """
    format_upper = format.upper()

    if format_upper == 'PNG':
        return embed_xmp_metadata_png(file_path, metadata)
    elif format_upper in ['TIFF', 'TIF']:
        return embed_xmp_metadata_tiff(file_path, metadata)
    elif format_upper in ['SVG', 'PDF', 'EPS']:
        # SVG und PDF haben bereits Metadaten-Support in matplotlib
        # Diese werden direkt über savefig() gesetzt
        return True
    else:
        return False
