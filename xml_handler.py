# xml_handler.py

import xml.etree.ElementTree as ET
import copy

class XMLHandler:
    """
    Helpers for reading and writing Eagle‐style library XML (.lbr/.xml), such that:

      • Whenever you add a <device> for package “X”, we scan the entire library
        (all devicesets) for any existing <device> whose @package or @name equals “X”.
        If we find one, we deep‐copy that <device> (which includes its <connects> block)
        into the new deviceset. That way every resistor, inductor, capacitor, etc. keeps
        the exact same pin‐to‐pad wiring the library originally defined.

      • If no existing <device> is found anywhere for package “X”, we create a brand‐new
        <device> with no <connects> (you can always hand‐edit or add defaults later).

      • All calls to create/merge will also write (or update) the <attribute name="DESCRIPTION">,
        <attribute name="LCSC_PART">, and <attribute name="VALUE"> tags under each <technology>.

    Usage is simply:
      • Load the library:                       tree = XMLHandler.parse_library(path)
      • Modify (create or merge devicesets)
      • Save the library:                       XMLHandler.save_library(tree, path)
    """

    @staticmethod
    def parse_library(path):
        """
        Parse an Eagle .lbr/.xml file from the given filesystem path and return its ElementTree.
        """
        return ET.parse(path)

    @staticmethod
    def save_library(tree, path):
        """
        Overwrite the original file with our modified tree (including XML declaration).
        """
        tree.write(path, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def list_packages(tree):
        """
        Return a sorted list of all <package name="..."> under <drawing><library><packages>.
        If <packages> is missing, returns an empty list.
        """
        root = tree.getroot()
        pk_parent = root.find("./drawing/library/packages")
        if pk_parent is None:
            return []
        names = [pkg.get("name") for pkg in pk_parent.findall("package") if pkg.get("name")]
        return sorted(names, key=lambda s: s.lower())

    @staticmethod
    def list_symbols(tree):
        """
        Return a sorted list of all <symbol name="..."> under <drawing><library><symbols>.
        If <symbols> is missing, returns an empty list.
        """
        root = tree.getroot()
        sym_parent = root.find("./drawing/library/symbols")
        if sym_parent is None:
            return []
        names = [sym.get("name") for sym in sym_parent.findall("symbol") if sym.get("name")]
        return sorted(names, key=lambda s: s.lower())

    @staticmethod
    def find_template_deviceset(tree):
        """
        Look for <deviceset name="DEVICE_NAME"> under <drawing><library><devicesets>.
        If not found, return the very first <deviceset> in that container.
        Raises RuntimeError if <devicesets> or any <deviceset> is missing.
        (You can still pass None for template_ds if you choose to skip using a template.)
        """
        root = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            raise RuntimeError("<devicesets> not found under <library>.")
        # Try to find “DEVICE_NAME” explicitly:
        for ds in ds_parent.findall("deviceset"):
            if ds.get("name") == "DEVICE_NAME":
                return ds
        # Otherwise return the first one:
        first = ds_parent.find("deviceset")
        if first is None:
            raise RuntimeError("No <deviceset> found under <devicesets>.")
        return first

    @staticmethod
    def extract_template_devices(template_ds):
        """
        Given a <deviceset> Element, collect all its <device> children into a dict:
          { package_name : <device>Element }
        Each value is a deep‐copiable Element (so we can clone the entire node, including <connects>).
        If <devices> is missing, returns an empty dict.
        """
        result = {}
        devs_parent = template_ds.find("devices")
        if devs_parent is None:
            return result
        for dev in devs_parent.findall("device"):
            pkg = dev.get("package") or dev.get("name")
            if pkg:
                result[pkg] = copy.deepcopy(dev)
        return result

    @staticmethod
    def get_existing_deviceset(tree, name):
        """
        Return the <deviceset> element whose @name matches 'name' case‐insensitively,
        or None if none found. Searches under <drawing><library><devicesets>.
        """
        root = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            return None
        target = name.lower()
        for ds in ds_parent.findall("deviceset"):
            if ds.get("name", "").lower() == target:
                return ds
        return None

    @staticmethod
    def _find_any_device_with_package(tree, pkg_name):
        """
        Search ​the entire library​ for a <device> whose @package or @name equals pkg_name.
        If found, return a ​deep‐copy​ of that <device> Element (including its <connects> block).
        Otherwise return None.

        We look under every <deviceset>:
          ./drawing/library/devicesets/deviceset/devices/device
        """
        root = tree.getroot()
        path = "./drawing/library/devicesets/deviceset"
        for ds in root.findall(path):
            devs_parent = ds.find("devices")
            if devs_parent is None:
                continue
            for dev in devs_parent.findall("device"):
                if dev.get("package") == pkg_name or dev.get("name") == pkg_name:
                    return copy.deepcopy(dev)
        return None

    @staticmethod
    def merge_into_deviceset(existing_ds, pkg_names, valid_pkgs, tree, template_dev_map=None, symbol_name=None):
        """
        Merge (add or update) the list of package names (pkg_names) into an existing <deviceset>.

        Arguments:
          - existing_ds:       the <deviceset> Element to modify
          - pkg_names:         list of footprint names (strings) chosen by the user
          - valid_pkgs:        dict { pkg_name: { "value": "...", "desc": "...", "lcsc": "..." } }
          - tree:              the entire ElementTree of the library (required to find existing connects)
          - template_dev_map:  optional dict { pkg_name: <device>Element } if you want to copy from a single “template” deviceset
                               (pass None if you don’t have a template)
          - symbol_name:       if provided, overrides <gate>@symbol inside <gates>

        Returns:
          (updated_count, added_count)
            updated_count = number of existing <device> nodes that got updated (only attributes changed)
            added_count   = number of brand‐new <device> nodes appended
        """
        if tree is None:
            raise RuntimeError("You must pass the full library tree to merge_into_deviceset().")

        updated_count = 0
        added_count = 0

        # 1) If symbol_name is provided, update all <gate> elements under <gates>
        if symbol_name:
            gates_parent = existing_ds.find("gates")
            if gates_parent is not None:
                for gate in gates_parent.findall("gate"):
                    gate.set("symbol", symbol_name)

        # 2) Ensure a <devices> container exists
        devs_parent = existing_ds.find("devices")
        if devs_parent is None:
            devs_parent = ET.SubElement(existing_ds, "devices")

        # 3) Build a quick map of existing <device name="..."> in this deviceset
        existing_map = {
            dev.get("name"): dev
            for dev in devs_parent.findall("device")
            if dev.get("name")
        }

        # 4) For each pkg_name the user wants to add/update:
        for pkg_name in pkg_names:
            vals = valid_pkgs.get(pkg_name, {})
            desc = vals.get("desc", "")
            lcsc = vals.get("lcsc", "")
            value = vals.get("value", "")

            # 4a) If a <device name="pkg_name"> already exists in this deviceset, update attributes
            if pkg_name in existing_map:
                dev_node = existing_map[pkg_name]

                # ● We do NOT touch <connects> here—whatever was already on that node remains intact.

                # Ensure <technologies><technology> exists
                tech_parent = dev_node.find("technologies")
                if tech_parent is None:
                    tech_parent = ET.SubElement(dev_node, "technologies")
                tech = tech_parent.find("technology")
                if tech is None:
                    tech = ET.SubElement(tech_parent, "technology")

                # Update the three <attribute> tags
                XMLHandler._set_or_update_attribute(tech, "DESCRIPTION", desc)
                XMLHandler._set_or_update_attribute(tech, "LCSC_PART", lcsc)
                XMLHandler._set_or_update_attribute(tech, "VALUE", value)

                updated_count += 1
                continue

            # 4b) Otherwise, we need to append a new <device> for pkg_name.
            #     We look for an existing device anywhere (to copy its <connects>).
            new_dev = None

            # If you provided a template map, try that first:
            if template_dev_map and pkg_name in template_dev_map:
                new_dev = copy.deepcopy(template_dev_map[pkg_name])
                new_dev.set("name", pkg_name)
                new_dev.set("package", pkg_name)
                # That cloned node already contains the correct <connects>.

            if new_dev is None:
                # Search the entire library for any device whose @package or @name == pkg_name
                found = XMLHandler._find_any_device_with_package(tree, pkg_name)
                if found is not None:
                    new_dev = found
                    new_dev.set("name", pkg_name)
                    new_dev.set("package", pkg_name)
                    # “found” is a deep copy, so its <connects> are preserved exactly.

            if new_dev is None:
                # No existing device anywhere → create brand‐new <device> without <connects>
                new_dev = ET.Element("device", {"name": pkg_name, "package": pkg_name})

            # 5) Ensure <technologies><technology> exists on new_dev, then set attributes:
            tech_parent = new_dev.find("technologies")
            if tech_parent is None:
                tech_parent = ET.SubElement(new_dev, "technologies")
            tech = tech_parent.find("technology")
            if tech is None:
                tech = ET.SubElement(tech_parent, "technology")

            XMLHandler._set_or_update_attribute(tech, "DESCRIPTION", desc)
            XMLHandler._set_or_update_attribute(tech, "LCSC_PART", lcsc)
            XMLHandler._set_or_update_attribute(tech, "VALUE", value)

            # 6) Append the new device to <devices>
            devs_parent.append(new_dev)
            added_count += 1

        return updated_count, added_count


    @staticmethod
    def create_new_deviceset(tree, template_ds, new_name, pkg_names, valid_pkgs, symbol_name=None):
        """
        Create a brand‐new <deviceset> under <drawing><library><devicesets> with the given name.

        Arguments:
          - tree:          the ElementTree of the library
          - template_ds:   a “template” <deviceset> to copy gates or devices from (optional; can be None)
          - new_name:      the new deviceset name (string)
          - pkg_names:     list of package strings to add
          - valid_pkgs:    dict { pkg_name: { desc, lcsc, value } }
          - symbol_name:   if provided, overrides <gate>@symbol under <gates>

        Behavior:
          1) Creates <deviceset name="new_name"/>.
          2) Copies <gates> from template_ds if provided (and applies symbol_name if not None).
          3) For each pkg_name, tries to copy an existing device (by searching entire library). If found, clones it
             (including <connects>). If not, makes an empty <device> with no <connects>.
          4) Always writes DESCRIPTION, LCSC_PART, and VALUE under each <device>.
        """
        root = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            # If <devicesets> doesn’t exist, create it under <library>
            lib_node = root.find("./drawing/library")
            if lib_node is None:
                raise RuntimeError("Cannot find <library> to attach <devicesets>.")
            ds_parent = ET.SubElement(lib_node, "devicesets")

        # 1) Create the new <deviceset>
        new_ds = ET.SubElement(ds_parent, "deviceset")
        new_ds.set("name", new_name)
        # Caller must set new_ds.set("prefix", ...) and new_ds.set("uservalue", "yes").

        # 2) Copy <gates> from template_ds if given
        if template_ds is not None:
            gates_parent = template_ds.find("gates")
            if gates_parent is not None:
                new_gates = copy.deepcopy(gates_parent)
                if symbol_name is not None:
                    for gate in new_gates.findall("gate"):
                        gate.set("symbol", symbol_name)
                new_ds.append(new_gates)
        else:
            # No template: user can insert a <gates> block manually later if needed.
            pass

        # 3) Create empty <devices> container
        new_devs_parent = ET.SubElement(new_ds, "devices")

        # 4) Build a template‐device map if template_ds is provided
        template_map = {}
        if template_ds is not None:
            template_map = XMLHandler.extract_template_devices(template_ds)

        # 5) For each pkg_name, try to copy an existing device anywhere in the library; else new blank
        for pkg_name in pkg_names:
            vals = valid_pkgs.get(pkg_name, {})
            desc = vals.get("desc", "")
            lcsc = vals.get("lcsc", "")
            value = vals.get("value", "")

            dev_elem = None

            if pkg_name in template_map:
                dev_elem = copy.deepcopy(template_map[pkg_name])
                dev_elem.set("name", pkg_name)
                dev_elem.set("package", pkg_name)

            if dev_elem is None:
                found = XMLHandler._find_any_device_with_package(tree, pkg_name)
                if found is not None:
                    dev_elem = found
                    dev_elem.set("name", pkg_name)
                    dev_elem.set("package", pkg_name)

            if dev_elem is None:
                # No existing device anywhere, so create blank <device>
                dev_elem = ET.Element("device", {"name": pkg_name, "package": pkg_name})

            # Ensure <technologies><technology> exists
            tech_parent = dev_elem.find("technologies")
            if tech_parent is None:
                tech_parent = ET.SubElement(dev_elem, "technologies")
            tech = tech_parent.find("technology")
            if tech is None:
                tech = ET.SubElement(tech_parent, "technology")

            # Write out the DESCRIPTION, LCSC_PART, and VALUE attributes
            XMLHandler._set_or_update_attribute(tech, "DESCRIPTION", desc)
            XMLHandler._set_or_update_attribute(tech, "LCSC_PART", lcsc)
            XMLHandler._set_or_update_attribute(tech, "VALUE", value)

            new_devs_parent.append(dev_elem)

        return new_ds

    @staticmethod
    def _set_or_update_attribute(tech_element, name, value):
        """
        In a <technology> element, find <attribute name="name">. If found, update @value.
        Otherwise, create a new <attribute> with constant="no".
        """
        for attr in tech_element.findall("attribute"):
            if attr.get("name") == name:
                attr.set("value", value)
                return
        new_attr = ET.SubElement(tech_element, "attribute")
        new_attr.set("name", name)
        new_attr.set("value", value)
        new_attr.set("constant", "no")
