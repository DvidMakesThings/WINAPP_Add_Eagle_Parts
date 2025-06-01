# xml_handler.py

import xml.etree.ElementTree as ET
import copy

class XMLHandler:
    """
    Provides static methods to parse, query, modify, and save an Eagle library XML (or .lbr).
    """

    @staticmethod
    def parse_library(path):
        """
        Parse the Eagle .lbr/.xml file and return an ElementTree.
        """
        return ET.parse(path)

    @staticmethod
    def save_library(tree, path):
        """
        Write the ElementTree back to disk (overwrite).
        """
        tree.write(path, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def find_template_deviceset(tree):
        """
        Look for a <deviceset name="DEVICE_NAME">. If not found, return the first <deviceset>.
        """
        root     = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            raise RuntimeError("<devicesets> not found in library.")

        # Try to find the one named "DEVICE_NAME"
        for ds in ds_parent.findall("deviceset"):
            if ds.get("name") == "DEVICE_NAME":
                return ds

        first = ds_parent.find("deviceset")
        if first is None:
            raise RuntimeError("No <deviceset> in library at all.")
        return first

    @staticmethod
    def extract_template_devices(template_ds):
        """
        Given a <deviceset> element, extract all its <device> child nodes,
        keyed by their @name (e.g. "0402", "0603", etc.). Returns a dict:
          { "0402": <device element>, "0603": <device element>, … }.
        We deepcopy each so they can be re‐inserted later.
        """
        result = {}
        devs_parent = template_ds.find("devices")
        if devs_parent is None:
            return result

        for dev in devs_parent.findall("device"):
            name = dev.get("name")
            if name:
                result[name] = copy.deepcopy(dev)
        return result

    @staticmethod
    def get_existing_deviceset(tree, name):
        """
        Return the <deviceset> element whose @name matches, or None if not found.
        """
        root     = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            return None
        for ds in ds_parent.findall("deviceset"):
            if ds.get("name") == name:
                return ds
        return None

    @staticmethod
    def merge_into_deviceset(existing_ds, pkg_names, template_devs, valid_pkgs):
        """
        Merge the given pkg_names into an existing <deviceset> element.
        - existing_ds: the <deviceset> element to update
        - pkg_names:   list of package names to include (["0402","0603",…])
        - template_devs: dict mapping pkg name → <device> template element
        - valid_pkgs: dict mapping pkg name → { "value": …, "desc": …, "lcsc": … }

        Returns (updated_count, added_count).
        """
        updated_count = 0
        added_count   = 0

        # Find—or create—<devices> under existing_ds
        devs_parent = existing_ds.find("devices")
        if devs_parent is None:
            devs_parent = ET.SubElement(existing_ds, "devices")

        # Build lookup of existing <device> nodes by @name
        existing_map = {dev.get("name"): dev for dev in devs_parent.findall("device")}

        for pkg_name in pkg_names:
            vals  = valid_pkgs[pkg_name]
            value = vals["value"]
            desc  = vals["desc"]
            lcsc  = vals["lcsc"]

            if pkg_name in existing_map:
                # ─── Update an existing <device> ───
                dev_node = existing_map[pkg_name]

                # Ensure <technologies><technology> exists
                tech_parent = dev_node.find("technologies")
                if tech_parent is None:
                    tech_parent = ET.SubElement(dev_node, "technologies")
                tech = tech_parent.find("technology")
                if tech is None:
                    tech = ET.SubElement(tech_parent, "technology")

                # For each attribute, set or update its @value
                XMLHandler._set_or_update_attribute(tech, "DESCRIPTION", desc)
                XMLHandler._set_or_update_attribute(tech, "LCSC_PART", lcsc)
                XMLHandler._set_or_update_attribute(tech, "VALUE", value)

                updated_count += 1

            else:
                # ─── Add a brand‐new <device> by copying from the template ───
                template_dev = template_devs.get(pkg_name)
                if template_dev is None:
                    # If no template exists for this package, skip entirely
                    continue

                new_dev = copy.deepcopy(template_dev)
                new_dev.set("name", pkg_name)

                # Inside the copied <device>, find or create <technologies><technology>
                tech_parent = new_dev.find("technologies")
                if tech_parent is None:
                    tech_parent = ET.SubElement(new_dev, "technologies")
                tech = tech_parent.find("technology")
                if tech is None:
                    tech = ET.SubElement(tech_parent, "technology")

                # Now set DESCRIPTION, LCSC_PART, VALUE (preserving spaces!)
                XMLHandler._set_or_update_attribute(tech, "DESCRIPTION", desc)
                XMLHandler._set_or_update_attribute(tech, "LCSC_PART", lcsc)
                XMLHandler._set_or_update_attribute(tech, "VALUE", value)

                devs_parent.append(new_dev)
                added_count += 1

        return updated_count, added_count

    @staticmethod
    def create_new_deviceset(tree, template_ds, new_name, pkg_names, valid_pkgs):
        """
        Create a new <deviceset> under <devicesets>, using template_ds’s <gates> and <symbol>.
        - new_name:   the name attribute of the new deviceset
        - pkg_names:  list of package names to add
        - valid_pkgs: dict mapping pkg name → { "value": …, "desc": …, "lcsc": … }

        Returns the newly appended <deviceset> element.
        """
        root      = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            # If <devicesets> does not exist, create it
            lib_parent = root.find("./drawing/library")
            if lib_parent is None:
                raise RuntimeError("Cannot find <library> to create <devicesets> under.")
            ds_parent = ET.SubElement(lib_parent, "devicesets")

        # Build new <deviceset> with name=new_name
        new_ds = ET.SubElement(ds_parent, "deviceset")
        new_ds.set("name", new_name)

        # Copy <gates> from template
        gates_parent = template_ds.find("gates")
        if gates_parent is not None:
            new_ds.append(copy.deepcopy(gates_parent))

        # Create <devices> block under new_ds
        new_devs_parent = ET.SubElement(new_ds, "devices")

        # Deep‐copy each <device> from the template map, then set its attributes
        template_dev_map = XMLHandler.extract_template_devices(template_ds)
        for pkg_name in pkg_names:
            vals  = valid_pkgs[pkg_name]
            value = vals["value"]
            desc  = vals["desc"]
            lcsc  = vals["lcsc"]

            template_dev = template_dev_map.get(pkg_name)
            if template_dev is None:
                continue

            new_dev = copy.deepcopy(template_dev)
            new_dev.set("name", pkg_name)

            tech_parent = new_dev.find("technologies")
            if tech_parent is None:
                tech_parent = ET.SubElement(new_dev, "technologies")
            tech = tech_parent.find("technology")
            if tech is None:
                tech = ET.SubElement(tech_parent, "technology")

            XMLHandler._set_or_update_attribute(tech, "DESCRIPTION", desc)
            XMLHandler._set_or_update_attribute(tech, "LCSC_PART", lcsc)
            XMLHandler._set_or_update_attribute(tech, "VALUE", value)

            new_devs_parent.append(new_dev)

        return new_ds

    @staticmethod
    def _set_or_update_attribute(tech_element, name, value):
        """
        Inside <technology>, find an <attribute name="…">.
        If found, update its @value. Otherwise create a fresh <attribute>.
        We do NOT split 'value' on spaces—so "10nF 10V" remains intact.
        """
        for attr in tech_element.findall("attribute"):
            if attr.get("name") == name:
                attr.set("value", value)
                return
        new_attr = ET.SubElement(tech_element, "attribute")
        new_attr.set("name", name)
        new_attr.set("value", value)
        new_attr.set("constant", "no")
