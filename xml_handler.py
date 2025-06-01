import xml.etree.ElementTree as ET

class XMLHandler:
    @staticmethod
    def parse_library(path):
        """
        Parse an Eagle .lbr or .xml library and return an ElementTree.
        """
        tree = ET.parse(path)
        return tree

    @staticmethod
    def find_template_deviceset(tree):
        """
        Return the <deviceset> element whose name="DEVICE_NAME", or
        if none, return the first <deviceset> under /drawing/library/devicesets.
        """
        root = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            raise RuntimeError("<devicesets> not found.")
        # First try to find name="DEVICE_NAME"
        for ds in ds_parent.findall("deviceset"):
            if ds.get("name") == "DEVICE_NAME":
                return ds
        # Fallback: return first deviceset
        first = ds_parent.find("deviceset")
        if first is None:
            raise RuntimeError("No <deviceset> in library.")
        return first

    @staticmethod
    def extract_template_devices(template_ds):
        """
        Given a <deviceset> element (template), return all its <device> nodes as a list.
        """
        devs_parent = template_ds.find("devices")
        if devs_parent is None:
            return []
        return devs_parent.findall("device")

    @staticmethod
    def get_existing_deviceset(tree, name):
        """
        Return the <deviceset> whose @name == name, or None if not found.
        """
        root = tree.getroot()
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
        Merge selected packages into an existing deviceset. Returns (updated_count, added_count).
        - existing_ds: the <deviceset> element to update
        - pkg_names: list of package names (strings) to insert/update
        - template_devs: list of <device> elements from the template
        - valid_pkgs: dict mapping pkg_name -> {"desc":..., "lcsc":...}
        """
        updated = 0
        added = 0

        # Build a map of existing package → <device> node inside existing_ds
        existing_map = { dev.get("package"): dev for dev in existing_ds.find("devices").findall("device") }

        for pkg in pkg_names:
            desc = valid_pkgs[pkg]["desc"]
            lcsc = valid_pkgs[pkg]["lcsc"]

            if pkg in existing_map:
                # update attributes under <technologies><technology>
                dev_node = existing_map[pkg]
                tech = dev_node.find("technologies/technology")
                if tech is None:
                    continue
                # Update the two <attribute> nodes
                for attr in tech.findall("attribute"):
                    if attr.get("name") == "DESCRIPTION":
                        attr.set("value", desc)
                    elif attr.get("name") == "LCSC_PART":
                        attr.set("value", lcsc)
                updated += 1
            else:
                # find the template <device> for this pkg, clone it, update attributes, then append
                template_node = None
                for tdev in template_devs:
                    if tdev.get("name") == pkg:
                        template_node = tdev
                        break
                if template_node is None:
                    continue
                # deep copy
                new_dev = XMLHandler._deep_copy_element(template_node)
                # set DESCRIPTION and LCSC_PART
                tech = new_dev.find("technologies/technology")
                if tech is not None:
                    for attr in tech.findall("attribute"):
                        if attr.get("name") == "DESCRIPTION":
                            attr.set("value", desc)
                        elif attr.get("name") == "LCSC_PART":
                            attr.set("value", lcsc)
                existing_ds.find("devices").append(new_dev)
                added += 1

        return updated, added

    @staticmethod
    def create_new_deviceset(tree, template_ds, new_name, pkg_names, valid_pkgs):
        """
        Create a brand‐new <deviceset> under /drawing/library/devicesets, copying the
        gates and template symbol, then inserting only the chosen pkgs.
        """
        root = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")

        # Clone the template <deviceset> structure (but rename it)
        new_ds = XMLHandler._deep_copy_element(template_ds)
        new_ds.set("name", new_name)

        # Remove all <device> children from new_ds, then re‐populate only the chosen ones
        devs_parent = new_ds.find("devices")
        if devs_parent is None:
            raise RuntimeError("Template has no <devices> section.")
        for d in list(devs_parent):
            devs_parent.remove(d)

        # Populate with selected packages
        template_devs = XMLHandler.extract_template_devices(template_ds)
        for pkg in pkg_names:
            desc = valid_pkgs[pkg]["desc"]
            lcsc = valid_pkgs[pkg]["lcsc"]
            # find the matching template <device>
            temp_node = next((td for td in template_devs if td.get("name") == pkg), None)
            if temp_node is None:
                continue
            new_dev = XMLHandler._deep_copy_element(temp_node)
            tech = new_dev.find("technologies/technology")
            if tech is not None:
                for attr in tech.findall("attribute"):
                    if attr.get("name") == "DESCRIPTION":
                        attr.set("value", desc)
                    elif attr.get("name") == "LCSC_PART":
                        attr.set("value", lcsc)
            devs_parent.append(new_dev)

        ds_parent.append(new_ds)

    @staticmethod
    def save_library(tree, path):
        """
        Write the modified ElementTree back to disk, preserving XML declaration.
        """
        tree.write(path, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _deep_copy_element(elem):
        """
        Return a deep‐copy of an ElementTree Element (and its children).
        """
        import copy
        return copy.deepcopy(elem)
