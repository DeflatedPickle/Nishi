#!/usr/bin/env python
# -*- coding: utf-8 -*-
""""""

import antlr4

from NishiLexer import NishiLexer
from NishiListener import NishiListener
from NishiParser import NishiParser

import io
from ast import literal_eval
import os
import sys
import argparse


class NishiTranspiler(NishiListener):
    def __init__(self, output: io.FileIO, pretty: bool=True):
        self.output = output

        self.pretty_print = pretty

        self.context = None
        self.context_type = ""
        self.access = None
        self.static = False
        self.package = False

        self.variable_contexts = {"classes": {},
                                  "functions": {}}

        self.indent = ""

        self.variables = {}

        self.python_to_csharp = {str: "string",
                                 int: "int",
                                 float: "float",
                                 list: "List<>",
                                 bool: "bool",
                                 None: "null"}

        self.carp_to_csharp = {"String": "string",
                               "Integer": "int",
                               "Float": "float",
                               "List": "List<>",
                               "Boolean": "bool",
                               "Void": "void",
                               "None": "null"}

        # self.insert_text("using System;{}using System.Collections.Generic".format("\n" if self.pretty_print else ""), 1, True)

    # Package

    def enterPackage(self, ctx:NishiParser.PackageContext):
        self.insert_text(f"namespace {ctx.ID()[0]} %s" % "{", 1)
        self.do_indent()

        self.package = True

    def exitProgram(self, ctx:NishiParser.ProgramContext):
        if self.package:
            self.context = None
            self.do_dedent()

            self.insert_text("}", 1)

    # Imports

    def enterImport_(self, ctx:NishiParser.Import_Context):
        packages = []

        for item in ctx.ID():
            packages.append(item.getText())

        self.insert_text(f"using {'.'.join(packages)}", 1, True)

    # Normal Classes

    def enterNormalClass(self, ctx:NishiParser.NormalClassContext):
        self.context = str(ctx.ID())
        self.context_type = "classes"
        self.variable_contexts["classes"][str(ctx.ID())] = []

        self.insert_text(f"class {str(ctx.ID())} %s" % "{", 1)

        self.do_indent()

    def exitNormalClass(self, ctx:NishiParser.NormalClassContext):
        self.context = None
        self.do_dedent()

        self.insert_text("}", 1)

    # Normal Functions

    def enterNormalFunction(self, ctx:NishiParser.NormalFunctionContext):
        if self.context is not None:
            void = " void" if self.context != str(ctx.ID()) else ""

            self.context = str(ctx.ID())
            self.context_type = "functions"
            self.variable_contexts["functions"][str(ctx.ID())] = []

            parameters = self.get_parameters(ctx.parameter())

            self.insert_text(f"public{void} {str(ctx.ID())}({', '.join(parameters)}) %s" % "{", 1)

        self.do_indent()

    def exitNormalFunction(self, ctx:NishiParser.NormalFunctionContext):
        # self.context = None
        self.do_dedent()

        self.insert_text("}", 1)

    # Override Functions

    def enterOverrideFunction(self, ctx:NishiParser.OverrideFunctionContext):
        if self.context is not None:
            self.context = str(ctx.ID())
            self.context_type = "functions"
            self.variable_contexts["functions"][str(ctx.ID())] = []

            parameters = self.get_parameters(ctx.parameter())

            self.insert_text(f"public override {str(ctx.ID())}({', '.join(parameters)}) %s" % "{", 1)

        self.do_indent()

    def exitOverrideFunction(self, ctx:NishiParser.OverrideFunctionContext):
        # self.context = None
        self.do_dedent()

        self.insert_text("}", 1)

    # Function Setters

    def enterFunctionSetter(self, ctx:NishiParser.FunctionSetterContext):
        if self.context is not None:
            self.context = str(ctx.ID())
            self.context_type = "functions"
            self.variable_contexts["functions"][str(ctx.ID())] = []

            parameters = self.get_parameters(ctx.parameter())

            self.insert_text(f"public {self.carp_to_csharp[str(ctx.type_().getText())]} {str(ctx.ID())}({', '.join(parameters)}) %s" % "{", 1)

        self.do_indent()

    def exitFunctionSetter(self, ctx:NishiParser.FunctionSetterContext):
        # self.context = None
        self.do_dedent()

        self.insert_text("}", 1)

    # Override Function Setters

    def enterOverrideFunctionSetter(self, ctx:NishiParser.OverrideFunctionSetterContext):
        if self.context is not None:
            self.context = str(ctx.ID())
            self.context_type = "functions"
            self.variable_contexts["functions"][str(ctx.ID())] = []

            parameters = self.get_parameters(ctx.parameter())

            self.insert_text(f"public override {str(ctx.ID())}({', '.join(parameters)}) %s" % "{", 1)

        self.do_indent()

    def exitOverrideFunctionSetter(self, ctx:NishiParser.OverrideFunctionSetterContext):
        # self.context = None
        self.do_dedent()

        self.insert_text("}", 1)

    # Function Call

    def enterCall_function(self, ctx:NishiParser.Call_functionContext):
        func = ctx.ID().getText()
        parameters = ctx.call_parameter()

        params = []
        par = 0

        for item in parameters:
            params.append(item.getText())

            if item.getText() != parameters[-1].getText():
                params.append(",")
                par += 1

        self.insert_text(f"{func}({' '.join(params)})", 1, True)

    # Create Class

    def enterClass_access(self, ctx:NishiParser.Class_accessContext):
        parameters = ctx.call_parameter()

        for clas in ctx.ID():
            clas = clas.getText()
            params = []
            par = 0

            for item in parameters:
                params.append(item.getText())

                if item.getText() != parameters[-1].getText():
                    params.append(",")
                    par += 1

            if clas in self.variable_contexts["classes"]:
                self.insert_text(f"new {clas}({' '.join(params)}){'.' if ctx.AT()[0] else ''}", 0, False)

            elif clas in self.variable_contexts["functions"][self.context]:
                self.insert_text(f"{clas}{'.' if ctx.AT()[0] else ''}", 0, False)

            else:
                self.insert_text(f"{clas}{'.' if ctx.AT()[0] and clas != ctx.ID()[-1].getText() else ''}", 1, True)

    # Private Block

    def enterPrivate_block(self, ctx:NishiParser.Private_blockContext):
        self.access = "private"

    def exitPrivate_block(self, ctx:NishiParser.Private_blockContext):
        self.access = None

    # Public Block

    def enterPublic_block(self, ctx:NishiParser.Public_blockContext):
        self.access = "public"

    def exitPublic_block(self, ctx:NishiParser.Public_blockContext):
        self.access = None

    # Static Block

    def enterStatic_block(self, ctx:NishiParser.Static_blockContext):
        self.static = True

    def exitStatic_block(self, ctx:NishiParser.Static_blockContext):
        self.static = False

    # Import Block

    def enterImport_item(self, ctx:NishiParser.Import_itemContext):
        imports = []

        for item in ctx.ID():
            imports.append(item.getText())

        self.insert_text(f"using {'.'.join(imports)}", 1, True)

    # Assignment

    def enterAssignment(self, ctx:NishiParser.AssignmentContext):
        type_ = ctx.type_().getText() if ctx.type_() is not None else None
        value = ctx.value().getText() if ctx.value() is not None else None
        class_var = True if str(ctx.ID()).startswith("this@") else False

        is_float = False
        multi_string = False
        capital_type = False

        string = []

        if self.access is not None:
            string.append(self.access)

        if self.static:
            string.append("static")

        if value:
            if value.startswith("`") and value.endswith("`"):
                multi_string = True
                value = value.replace("`", "\"")
                value = "\\n".join(value.splitlines())

        if str(ctx.ID()) not in self.variable_contexts[self.context_type][self.context] and type_ is None:
            if value and self.access is not None:
                string.append(self.convert_types(type(literal_eval(value))))

            elif value and self.access is None and not class_var and type_ is None:
                string.append("var")

            try:
                if self.convert_types(type(literal_eval(value))) == "float":
                        is_float = True

            except ValueError:
                pass

        if self.convert_types(type_) == "float":
            is_float = True

        if type_:
            string.append(self.convert_types(type_))

            if not self.istype(type_):
                if type_[0].isupper():
                    capital_type = True

        string.append(f"{ctx.ID()}")

        if value:
            if value.split("(")[0] in self.variable_contexts["classes"]:
                self.insert_text(f"{' '.join(string)} = ")
                return

            elif value.split("(")[0] in self.carp_to_csharp.keys():
                capital_type = True

            elif value[0].isupper() and value.split("<")[0] in self.carp_to_csharp.keys():
                capital_type = True

        if value:
            if value.startswith("'") and value.endswith("'"):
                value = value.replace("'", "\"").replace("\\", "\\\\")

            if multi_string:
                value = value.replace("\"\"\"", "@\"", 1).replace("\"\"\"", "\"", 1)

            if "@" in value:
                self.insert_text(f"{' '.join(string)} = {value.split('@')[0]}.")
                return

            string.append(f"= {'new ' if capital_type else ''}{value}{'f' if is_float else ''}")

        self.variable_contexts[self.context_type][self.context].append(str(ctx.ID()))

        self.insert_text(f"{' '.join(string).replace('this@', '').replace('@', '.')}", 1, True)
        # self.insert_text(f"{' '.join(string).replace('this@', '').replace('@', '.')}", 1, True)

    # Print

    def enterPrint_(self, ctx:NishiParser.Print_Context):
        values = [i.getText() for i in ctx.value()]

        if ctx.PRINTLN():
            values.append('"\\n"')

        prints = []

        for item in values:
            prints.append(f"System.Console.Write({item})")

        self.insert_text("; ".join(prints), 1, True)

    def enterReturn_(self, ctx:NishiParser.Return_Context):
        value = ctx.value()
        expression = ctx.expression()

        self.insert_text(f"return {value.getText() if value is not None else expression.getText()}", 1, True)

    # If

    def enterIf_(self, ctx:NishiParser.If_Context):
        self.insert_text(f"if ({ctx.getText().split('{')[0].replace('if', '')}) %s" % "{", 1)

        self.do_indent()

    def exitIf_(self, ctx:NishiParser.If_Context):
        self.do_dedent()

        self.insert_text("}", 1)

    # Else if

    def enterElif_(self, ctx:NishiParser.Elif_Context):
        self.insert_text(f"else if ({ctx.getText().split('{')[0].replace('elf', '')}) %s" % "{", 1)

        self.do_indent()

    def exitElif_(self, ctx:NishiParser.Elif_Context):
        self.do_dedent()

        self.insert_text("}", 1)

    # Else

    def enterElse_(self, ctx:NishiParser.Else_Context):
        self.insert_text("else {", 1)

        self.do_indent()

    def exitElse_(self, ctx:NishiParser.Else_Context):
        self.do_dedent()

        self.insert_text("}", 1)

    # Other Methods

    def do_indent(self):
        self.indent += " " * 4

    def do_dedent(self):
        self.indent = self.indent[:-4]

    def insert_text(self, text: str, newlines: int=0, line_end: bool=False):
        if self.pretty_print:
            self.output.write(f"{self.indent}{text}{';' if line_end else ''}{os.linesep * newlines}")

        else:
            self.output.write(f"{text}{';' if line_end else ''}")

        # print(self.context, self.variable_contexts)

    def get_parameters(self, ctxparameter):
        parameters = []

        for item in ctxparameter:
            name = item.ID().getText()

            param = []

            if item.type_():
                type_ = item.type_().getText()
                param.append(self.carp_to_csharp[type_])

            param.append(name)

            if item.value():
                value = item.value().getText()
                param.append(f"= {value}")

            parameters.append(" ".join(param))

        return parameters

    def convert_types(self, type_):
        try:
            return self.carp_to_csharp[type_]

        except KeyError:
            try:
                return self.python_to_csharp[type_]

            except KeyError:
                return "var"  # type_

    def istype(self, type_):
        if type_ in self.python_to_csharp.keys():
            return True

        elif type_ in self.carp_to_csharp.keys():
            return True

        else:
            return False


if __name__ == "__main__":
    parse_args = argparse.ArgumentParser()
    parse_args.add_argument("-f", "--file", type=str, help="the Nishi file")
    parse_args.add_argument("-p", "--pretty", action="store_true", help="pretty print the C# file")
    args = parse_args.parse_args()

    file = args.file
    pretty = args.pretty

    # file = "examples/simple_class.nishi"
    # pretty = True

    if file is None:
        sys.exit()

    lexerer = NishiLexer(antlr4.FileStream(file))
    stream = antlr4.CommonTokenStream(lexerer)
    parser = NishiParser(stream)
    tree = parser.program()

    with open(f"{str(file).split('.')[0]}.cs", "w") as out:
        interpreter = NishiTranspiler(out, pretty)
        walker = antlr4.ParseTreeWalker()
        walker.walk(interpreter, tree)
