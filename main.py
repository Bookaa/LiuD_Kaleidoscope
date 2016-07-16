#!/usr/bin/env python

# refer to https://github.com/eliben/pykaleidoscope/blob/master/chapter6.py

from ctypes import CFUNCTYPE, c_double

import llvmlite.ir as ir
import llvmlite.binding as llvm

import Ast_Ks

class LLVMCodeGenerator:
    def __init__(self):
        self.module = ir.Module()
        self.builder = None
        self.func_symtab = {}

    def generate_code(self, node):
        return self._codegen(node)

    def _codegen(self, node):
        if isinstance(node, Ast_Ks.ks_Module):
            return self._codegen_Module(node)
        if isinstance(node, Ast_Ks.ks_funcdef):
            return self._codegen_funcdef(node)
        if isinstance(node, Ast_Ks.ks_enclosed):
            return self._codegen(node.v)
        if isinstance(node, Ast_Ks.ks_ifcmd):
            return self._codegen_ifcmd(node)
        if isinstance(node, Ast_Ks.ks_body):
            ret = None
            for v in node.vlst:
                ret = self._codegen(v)
            return ret
        if isinstance(node, Ast_Ks.ks_value):
            lhs = self._codegen(node.v1)
            rhs = self._codegen(node.v2)
            op = node.s
            if op == '+':
                return self.builder.fadd(lhs, rhs, 'addtmp')
            if op == '-':
                return self.builder.fsub(lhs, rhs, 'subtmp')
            if op == '*':
                return self.builder.fmul(lhs, rhs, 'multmp')
            if op == '<':
                return self.builder.fcmp_unordered('<', lhs, rhs, 'cmptmp')
            if op == '>':
                return self.builder.fcmp_unordered('>', lhs, rhs, 'cmptmp')
            if op == '|':
                one = ir.Constant(ir.IntType(1), 1)
                zero = ir.Constant(ir.IntType(1), 0)
                return self._codegen_ifcmd_2([(lhs, one), (rhs, one)], zero)
            assert False
        if isinstance(node, Ast_Ks.ks_litVarname):
            return self.func_symtab[node.n]
        if isinstance(node, Ast_Ks.ks_litNumi):
            return ir.Constant(ir.DoubleType(), float(node.i))
        if isinstance(node, Ast_Ks.ks_litNumf):
            return ir.Constant(ir.DoubleType(), float(node.f))
        if isinstance(node, Ast_Ks.ks_funccall):
            return self._codegen_funccall(node)
        if isinstance(node, Ast_Ks.ks_forcmd):
            return self._codegen_forcmd(node)
        if isinstance(node, Ast_Ks.ks_negitem):
            if isinstance(node.v, Ast_Ks.ks_litNumf):
                return ir.Constant(ir.DoubleType(), -float(node.v.f))
            value = self._codegen(node.v)
            zero = ir.Constant(ir.DoubleType(), 0.0)
            return self.builder.fsub(zero, value)
        print 'not find _codegen for', node
        assert False

    def _codegen_Module(self, node):
        n = 0
        for v in node.vlst:
            if isinstance(v, Ast_Ks.ks_funcdef):
                self._codegen(v)
                continue
            n += 1
            name = '_anon%d' % n
            self.func_symtab = {}
            func_ty = ir.FunctionType(ir.DoubleType(),[])
            func = ir.Function(self.module, func_ty, name)

            bb_entry = func.append_basic_block('entry')
            self.builder = ir.IRBuilder(bb_entry)
            retval = self._codegen(v)
            self.builder.ret(retval)
        return name

    def _codegen_funcdef(self, node):
        self.func_symtab = {}
        func = self._codegen_PrototypeAST(node)
        bb_entry = func.append_basic_block('entry')
        self.builder = ir.IRBuilder(bb_entry)
        retval = self._codegen(node.v)  # node.v is body
        self.builder.ret(retval)
        return func

    def _codegen_ifcmd(self, node):
        lst = [(node.v1, node.v2)]
        for elsecl in node.vlst:
            lst.append((elsecl.v1, elsecl.v2))
        return self._codegen_ifcmd_1(lst, node.v4)

    def _codegen_ifcmd_1(self, lst, last_else):
        (cond_expr, then_expr) = lst.pop(0)
        cond_val = self._codegen(cond_expr)
        cmp = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(ir.IntType(1), 0))

        then_bb = self.builder.function.append_basic_block('then')
        else_bb = ir.Block(self.builder.function, 'else')
        merge_bb = ir.Block(self.builder.function, 'ifcont')
        self.builder.cbranch(cmp, then_bb, else_bb)

        self.builder.position_at_start(then_bb)
        then_val = self._codegen(then_expr)
        self.builder.branch(merge_bb)

        then_bb = self.builder.block

        self.builder.function.basic_blocks.append(else_bb)
        self.builder.position_at_start(else_bb)
        if not lst:
            else_val = self._codegen(last_else)
        else:
            else_val = self._codegen_ifcmd_1(lst, last_else)

        else_bb = self.builder.block
        self.builder.branch(merge_bb)

        self.builder.function.basic_blocks.append(merge_bb)
        self.builder.position_at_start(merge_bb)
        phi = self.builder.phi(ir.DoubleType(), 'iftmp')
        phi.add_incoming(then_val, then_bb)
        phi.add_incoming(else_val, else_bb)
        return phi

    def _codegen_ifcmd_2(self, lst, last_else):
        (cond_val, then_val) = lst.pop(0)
        cmp = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(ir.IntType(1), 0))

        then_bb = self.builder.function.append_basic_block('then')
        else_bb = ir.Block(self.builder.function, 'else')
        merge_bb = ir.Block(self.builder.function, 'ifcont')
        self.builder.cbranch(cmp, then_bb, else_bb)

        self.builder.position_at_start(then_bb)
        self.builder.branch(merge_bb)

        then_bb = self.builder.block

        self.builder.function.basic_blocks.append(else_bb)
        self.builder.position_at_start(else_bb)
        if not lst:
            else_val = last_else
        else:
            else_val = self._codegen_ifcmd_2(lst, last_else)

        else_bb = self.builder.block
        self.builder.branch(merge_bb)

        self.builder.function.basic_blocks.append(merge_bb)
        self.builder.position_at_start(merge_bb)
        phi = self.builder.phi(ir.IntType(32), 'iftmp')
        phi.add_incoming(then_val, then_bb)
        phi.add_incoming(else_val, else_bb)
        return phi

    def _codegen_PrototypeAST(self, node):
        funcname = node.n
        func_ty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()] * len(node.vlst))

        # If a function with this name already exists in the module...
        if funcname in self.module.globals:
            # We only allow the case in which a declaration exists and now the
            # function is defined (or redeclared) with the same number of args.
            existing_func = self.module[funcname]
            if not isinstance(existing_func, ir.Function):
                raise CodegenError('Function/Global name collision', funcname)
            if not existing_func.is_declaration():
                raise CodegenError('Redifinition of {0}'.format(funcname))
            if len(existing_func.function_type.args) != len(func_ty.args):
                raise CodegenError('Redifinition with different number of arguments')
            func = self.module.globals[funcname]
        else:
            # Otherwise create a new function
            func = ir.Function(self.module, func_ty, funcname)
        # Set function argument names from AST
        for i, arg in enumerate(func.args):
            arg.name = node.vlst[i].n
            self.func_symtab[arg.name] = arg
        return func

    def _codegen_funccall(self, node):
        callee = node.n
        callee_func = self.module.get_global(callee)
        if callee_func is None or not isinstance(callee_func, ir.Function):
            raise CodegenError('Call to unknown function', callee)
        len_args = 0
        if node.vq:
            len_args = len(node.vq.vlst)
        if len(callee_func.args) != len_args:
            raise CodegenError('Call argument length mismatch', callee)
        call_args = []
        if node.vq:
            call_args = [self._codegen(arg) for arg in node.vq.vlst]
        return self.builder.call(callee_func, call_args, 'calltmp')

    def _codegen_forcmd(self, node):
        # Output this as:
        #   ...
        #   start = startexpr
        #   goto loop
        # loop:
        #   variable = phi [start, loopheader], [nextvariable, loopend]
        #   ...
        #   bodyexpr
        #   ...
        # loopend:
        #   step = stepexpr
        #   nextvariable = variable + step
        #   endcond = endexpr
        #   br endcond, loop, endloop
        # outloop:

        # Emit the start expr first, without the variable in scope.
        id_name = node.v1.n
        start_expr = node.v1.v
        if isinstance(node.v4.v, Ast_Ks.ks_forbody1):
            body = node.v4.v.v
        else:
            body = node.v4.v
        step_expr = node.v3
        end_expr = node.v2

        start_val = self._codegen(start_expr)
        preheader_bb = self.builder.block
        loop_bb = self.builder.function.append_basic_block('loop')

        # Insert an explicit fall through from the current block to loop_bb
        self.builder.branch(loop_bb)
        self.builder.position_at_start(loop_bb)

        # Start the PHI node with an entry for start
        phi = self.builder.phi(ir.DoubleType(), id_name)
        phi.add_incoming(start_val, preheader_bb)

        # Within the loop, the variable is defined equal to the PHI node. If it
        # shadows an existing variable, we have to restore it, so save it now.
        oldval = self.func_symtab.get(id_name)
        self.func_symtab[id_name] = phi

        # Emit the body of the loop. This, like any other expr, can change the
        # current BB. Note that we ignore the value computed by the body.
        body_val = self._codegen(body)

        if step_expr is None:
            stepval = ir.Constant(ir.DoubleType(), 1.0)
        else:
            stepval = self._codegen(step_expr)
        nextvar = self.builder.fadd(phi, stepval, 'nextvar')

        # Compute the end condition
        endcond = self._codegen(end_expr)
        cmp = self.builder.icmp_unsigned('!=', endcond, ir.Constant(ir.IntType(1), 0), 'loopcond')

        # Create the 'after loop' block and insert it
        loop_end_bb = self.builder.block
        after_bb = self.builder.function.append_basic_block('afterloop')

        # Insert the conditional branch into the end of loop_end_bb
        self.builder.cbranch(cmp, loop_bb, after_bb)

        # New code will be inserted into after_bb
        self.builder.position_at_start(after_bb)

        # Add a new entry to the PHI node for the backedge
        phi.add_incoming(nextvar, loop_end_bb)

        # Remove the loop variable from the symbol table; if it shadowed an
        # existing variable, restore that.
        if oldval is None:
            del self.func_symtab[id_name]
        else:
            self.func_symtab[id_name] = oldval

        # The 'for' expression always returns 0
        return ir.Constant(ir.DoubleType(), 0.0)

class KaleidoscopeEvaluator(object):
    def __init__(self):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

        self.codegen = LLVMCodeGenerator()
        self._add_builtins(self.codegen.module)

        self.target = llvm.Target.from_default_triple()

    def evaluate(self, ast):
        return self.codegen.generate_code(ast)

    def _add_builtins(self, module):
        putchar_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(32)])
        putchar = ir.Function(module, putchar_ty, 'putchar')

        putchard_ty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()])
        putchard = ir.Function(module, putchard_ty, 'putchard')
        irbuilder = ir.IRBuilder(putchard.append_basic_block('entry'))
        ival = irbuilder.fptoui(putchard.args[0], ir.IntType(32), 'intcast')
        irbuilder.call(putchar, [ival])
        irbuilder.ret(ir.Constant(ir.DoubleType(), 0))


def generate_mandelbrot(codestr, optimize=False, llvmdump=False, asmdump=False):
    e = KaleidoscopeEvaluator()

    ast = Ast_Ks.Test_Parse_ks(codestr)

    main_name = e.evaluate(ast)

    if llvmdump:
        print('======== Unoptimized LLVM IR')
        print(str(e.codegen.module))

    ss = str(e.codegen.module)
    llvmmod = llvm.parse_assembly(ss)

    # Optimize the module
    if optimize:
        pmb = llvm.create_pass_manager_builder()
        pmb.opt_level = 2
        pm = llvm.create_module_pass_manager()
        pmb.populate(pm)
        pm.run(llvmmod)

        if llvmdump:
            print('======== Optimized LLVM IR')
            print(str(llvmmod))

    target_machine = e.target.create_target_machine()
    with llvm.create_mcjit_compiler(llvmmod, target_machine) as ee:
        ee.finalize_object()

        if asmdump:
            print('======== Machine code')
            print(target_machine.emit_assembly(llvmmod))

        fptr = CFUNCTYPE(c_double)(ee.get_function_address(main_name))
        result = fptr()
        return result


if __name__ == '__main__':
    generate_mandelbrot(Ast_Ks.s_sample_ks)
