__version__ = "1.0.0"

import sys
import inspect
import importlib.util
from pathlib import Path
from textwrap import dedent

class DocGenerator:
    """
    EPY service responsible for generating technical documentation.
    Class for handling documentation about Python modules in current project

    This class introspects both EssencePy internal modules (bootstrap) 
    and user-defined modules (lib/) to extract:
        - public classes
        - public methods
        - associated docstrings

    The output is a Markdown file.
    """

    def __init__(self, app_home, app_name):
        """
        Constructor.

        Args:
            app_home (str | Path): Root directory of the application.
            app_name (str): Application name.
        """
        self.application_home = Path(app_home).resolve()
        self.application_name = app_name

        # Main library directory
        self.lib_dir = self.application_home / "lib"

        # EssencePy bootstrap directory (auto-loaded modules)
        self.bootstrap_dir = self.lib_dir / "bootstrap"

    # ------------------------------------------------------------------ #
    # Documentary module loading
    # ------------------------------------------------------------------ #

    def _load_module_for_doc(self, module_name):
        """
        Load a Python module only for documentation purposes.

        This method dynamically loads a module from the lib/ directory
        without registering it as a runtime dependency of EPY.

        Args:
            module_name (str): Module filename without extension.

        Returns:
            module: Loaded Python module.

        Raises:
            ModuleNotFoundError: If the module file does not exist.
        """
        module_path = self.lib_dir / f"{module_name}.py"
        if not module_path.exists():
            raise ModuleNotFoundError(module_name)

        spec = importlib.util.spec_from_file_location(
            module_name,
            module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _normalize_target(self, target):
        """
        Normalize the target argument provided by the user.

        The target can designate either:
            - a module (file name)
            - a class (class name)

        Convention:
            - Uppercase first letter → class
            - Lowercase → module

        Args:
            target (str | None): User input target.

        Returns:
            tuple:
                - target_module (str | None)
                - target_class (str | None)
        """
        if not target:
            return None, None

        target = target.replace(".py", "")

        if target[0].isupper():
            return None, target   # class target
        else:
            return target, None   # module target

    # ------------------------------------------------------------------ #
    # Module collection
    # ------------------------------------------------------------------ #

    def _collect_epy_modules(self):
        """
        Collect already-loaded EssencePy bootstrap modules.

        These modules are detected from sys.modules and filtered
        based on their physical location in lib/bootstrap.

        Returns:
            dict[str, module]: Mapping of module names to module objects.
        """
        modules = {}

        for module in sys.modules.values():
            file = getattr(module, "__file__", None)
            if not file:
                continue

            path = Path(file).resolve()
            if self.bootstrap_dir in path.parents:
                modules[module.__name__] = module

        return modules

    def _collect_user_modules(self, existing, target_module=None):
        """
        Collect user-defined modules located in lib/.

        Modules are dynamically loaded only if:
            - they are not already loaded by EPY
            - they match the optional target_module filter

        Args:
            existing (dict): Already loaded modules.
            target_module (str | None): Specific module to document.

        Returns:
            dict[str, module]: Loaded user modules.
        """
        modules = {}

        for py in self.lib_dir.glob("*.py"):
            name = py.stem

            # Skip non-targeted modules
            if target_module and name != target_module:
                continue

            # Skip already loaded modules
            if name in existing:
                continue

            try:
                modules[name] = self._load_module_for_doc(name)
            except Exception:
                # Ignore faulty or non-loadable modules
                continue

        return modules

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #

    def _is_public(self, name):
        """
        Determine if a symbol is public.

        Private symbols (starting with "_") are excluded
        from the documentation.

        Args:
            name (str): Symbol name.

        Returns:
            bool: True if public, False otherwise.
        """
        return not name.startswith("_")

    def _extract_module_api(self, module, target_class=None):
        """
        Extract the public API of a module.

        This includes:
            - public classes
            - public methods of those classes
            - associated docstrings

        Args:
            module (module): Python module to introspect.
            target_class (str | None): Optional class filter.

        Returns:
            dict: Structured API representation.
        """
        api = {
            "module": module.__name__,
            "file": getattr(module, "__file__", ""),
            "doc": inspect.getdoc(module),
            "functions": [],
            "classes": [],
        }

        for name, obj in inspect.getmembers(module):

            # Skip private symbols
            if not self._is_public(name):
                continue

            # Classes defined in this module only
            if inspect.isclass(obj) and obj.__module__ == module.__name__:

                # Apply class filter if defined
                if target_class and name != target_class:
                    continue

                methods = []
                for m_name, m_obj in inspect.getmembers(obj, inspect.isfunction):
                    if (
                        self._is_public(m_name)
                        and m_obj.__qualname__.startswith(obj.__name__)
                    ):
                        methods.append({
                            "name": m_name,
                            "signature": str(inspect.signature(m_obj)),
                            "doc": inspect.getdoc(m_obj),
                        })

                api["classes"].append({
                    "name": name,
                    "doc": inspect.getdoc(obj),
                    "methods": methods,
                })

        return api

    # ------------------------------------------------------------------ #
    # Markdown generation
    # ------------------------------------------------------------------ #

    def _format_docstring(self, doc):
        """
        Convert Python docstrings (Google / NumPy style) into readable Markdown.
        """
        if not doc:
            return ""

        lines = dedent(doc).strip().splitlines()
        out = []

        section = None
        args = []
        returns = []
        examples = []
        block = []

        def flush_args():
            if args:
                out.append("\n**Arguments**\n")
                out.append("| Name | Description |")
                out.append("|------|-------------|")
                out.extend(args)
                args.clear()

        def flush_returns():
            if returns:
                out.append("\n**Returns**\n")
                for r in returns:
                    out.append(f"- {r}")
                returns.clear()

        for line in lines:
            s = line.strip()

            # ---------------- Sections ----------------
            if s in ("Args:", "Arguments:", "Parameters"):
                flush_args()
                flush_returns()
                section = "args"
                continue

            if s in ("Returns:", "Return"):
                flush_args()
                section = "returns"
                continue

            if s in ("Example:", "Examples:"):
                flush_args()
                flush_returns()
                section = "example"
                continue

            # NumPy underline style
            if set(s) == {"-"}:
                continue

            # ---------------- Content ----------------
            if section == "args" and ":" in s:
                name, desc = s.split(":", 1)
                args.append(f"| `{name.strip()}` | {desc.strip()} |")
                continue

            if section == "returns" and s:
                returns.append(s)
                continue

            if section == "example":
                examples.append(line)
                continue

            # Notes / warnings
            if s.lower().startswith("note:"):
                out.append(f"\n> **Note:** {s[5:].strip()}")
                continue

            if s.lower().startswith("warning:"):
                out.append(f"\n> **Warning:** {s[8:].strip()}")
                continue

            # Normal text
            if s:
                out.append(s)
            else:
                out.append("")

        flush_args()
        flush_returns()

        # Example block
        if examples:
            out.append("\n**Example**\n")  # force blank line before & after block
            out.append("```python")
            for line in examples:
                out.append(line.lstrip())  # align left, remove indentation
            out.append("```")

        return "\n".join(out)


    def _indent(self, text, level=1):
        prefix = " " * (level * 2)
        return "\n".join(prefix + line if line else "" for line in text.splitlines())


    def _to_markdown(self, apis):
        """
        Convert extracted APIs into a Markdown document.

        Args:
            apis (list[dict]): Extracted module APIs.

        Returns:
            str: Markdown content.
        """
        md = []
        md.append(f"# Technical documentation – {self.application_name}\n")
        md.append("> [!NOTE]\n> _This file was automatically created by EssencePy_")

        for api in sorted(apis, key=lambda x: x["module"]):
            md.append(f"\n## Module `{api['module']}`\n")
            md.append(f"*Source* : `{api['file']}`\n")

            if api["doc"]:
                md.append(dedent(api["doc"]) + "\n")

            for cls in api["classes"]:
                md.append(f"\n### Class `{cls['name']}`\n")
                if cls["doc"]:
                    # md.append(dedent(cls["doc"]) + "\n")
                    md.append(self._format_docstring(cls["doc"]) + "\n")


                for m in cls["methods"]:
                    md.append(f"- **{m['name']}{m['signature']}**")
                    if m["doc"]:
                        # md.append(f"\n  {dedent(m['doc'])}")
                        md.append("\n" + self._indent(self._format_docstring(m["doc"]), level=2))


            if api["functions"]:
                md.append("\n### Functions\n")
                for fn in api["functions"]:
                    md.append(f"- **{fn['name']}{fn['signature']}**")
                    if fn["doc"]:
                        md.append(f"\n  {dedent(fn['doc'])}")

        return "\n".join(md)

    # ------------------------------------------------------------------ #
    # Public EPY API
    # ------------------------------------------------------------------ #

    def generate(self, target_module=None, output_filename=None) -> None:
        """
        Generate the technical documentation of current project or a specified module/class.
        Output files will be stored into `<application_home>/docs`.

        Args:
            target_module (str, optional): module or class name (None for document everything)
            output_filename (str, optional): Output filename (None = <application_name>_technical_doc.md)

        Example:
            # Generate full project documentation with default output name 
            epy.doc.generate()

            # Generate full project documentation with custom output name
            epy.doc.generate(output_filename='my_custom_doc.md')

            # Generate module documentation with custom output name
            epy.doc.generate(target_module='my_dummy_class', output_filename='my_dummy_class.md')
        """
        # Ensure documentation output directory exists
        output_path = self.application_home / "docs"
        output_path.mkdir(parents=True, exist_ok=True)

        # Determine output file name
        if output_filename:
            output_file = output_path / output_filename
        else:
            output_file = output_path / f"{self.application_name}_technical_doc.md"

        # Normalize user target
        target_mod, target_class = self._normalize_target(target_module)

        # Collect modules
        epy_modules = self._collect_epy_modules()
        user_modules = self._collect_user_modules(
            existing=epy_modules,
            target_module=target_mod
        )

        # If a specific target is defined, only document user modules
        if target_module:
            all_modules = {**user_modules}
        else:
            all_modules = {**epy_modules, **user_modules}

        # Extract APIs
        apis = [
            self._extract_module_api(m, target_class)
            for m in all_modules.values()
        ]

        # Remove empty modules
        apis = [a for a in apis if a["classes"] or a["functions"]]

        # Write Markdown file
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(self._to_markdown(apis))
            file.close()
