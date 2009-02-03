#!/usr/bin/python -O
# -*- coding: iso-8859-1 -*-
#    Molecule Disc Image builder for Sabayon Linux
#    Copyright (C) 2009 Fabio Erculiani
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from __future__ import with_statement
import os
import shutil
from molecule.i18n import _
from molecule.output import red, brown, blue, green, purple, darkgreen, darkred, bold, darkblue, readtext
from molecule.exception import EnvironmentError, NotImplementedError
import molecule.utils

# This is an interface that has to be reimplemented in order to make it doing something useful
class GenericHandlerInterface:

    def __init__(self, spec_path, metadata):
        from molecule import Output, Config
        self.Output = Output
        self.Config = Config
        self.spec_path = spec_path
        self.metadata = metadata
        self.spec_name = os.path.basename(self.spec_path)

    def pre_run(self):
        raise NotImplementedError("NotImplementedError: this needs to be reimplemented")

    def run(self):
        raise NotImplementedError("NotImplementedError: this needs to be reimplemented")

    def post_run(self):
        raise NotImplementedError("NotImplementedError: this needs to be reimplemented")

    def kill(self):
        raise NotImplementedError("NotImplementedError: this needs to be reimplemented")

class MirrorHandler(GenericHandlerInterface):

    def __init__(self, *args, **kwargs):
        GenericHandlerInterface.__init__(self, *args, **kwargs)

    def pre_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("MirrorHandler"),darkred(self.spec_name),_("executing pre_run"),))

        # creating destination chroot dir
        self.source_dir = self.metadata['source_chroot']
        self.dest_dir = os.path.join(self.metadata['destination_chroot'],"chroot",os.path.basename(self.source_dir))
        if not os.path.isdir(self.dest_dir):
            os.makedirs(self.dest_dir,0755)

        return 0

    def post_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("MirrorHandler"),darkred(self.spec_name),_("executing post_run"),))
        return 0

    def kill(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("MirrorHandler"),darkred(self.spec_name),_("executing kill"),))
        return 0

    def run(self):

        self.Output.updateProgress("[%s|%s] %s" % (blue("MirrorHandler"),darkred(self.spec_name),_("mirroring running"),))
        # running sync
        args = [self.Config['mirror_syncer']]
        args.extend(self.Config['mirror_syncer_builtin_args'])
        args.extend(self.metadata.get('extra_rsync_parameters',[]))
        args.extend([self.source_dir+"/*",self.dest_dir])
        self.Output.updateProgress("[%s|%s] %s: %s" % (blue("MirrorHandler"),darkred(self.spec_name),_("spawning"),args,))
        rc = molecule.utils.exec_cmd(args)
        if rc != 0:
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("MirrorHandler"),darkred(self.spec_name),_("mirroring failed"),rc,))
            return rc

        self.Output.updateProgress("[%s|%s] %s" % (blue("MirrorHandler"),darkred(self.spec_name),_("mirroring completed successfully"),))
        return 0

class ChrootHandler(GenericHandlerInterface):

    def __init__(self, *args, **kwargs):
        GenericHandlerInterface.__init__(self, *args, **kwargs)

    def pre_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("executing pre_run"),))
        self.source_dir = self.metadata['source_chroot']
        self.dest_dir = os.path.join(self.metadata['destination_chroot'],"chroot",os.path.basename(self.source_dir))
        return 0

    def post_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("executing post_run"),))

        # write release file
        release_file = self.metadata.get('release_file')
        if release_file:
            release_file = os.path.join(self.dest_dir,release_file)
            if os.path.lexists(release_file) and not os.path.isfile(release_file):
                self.Output.updateProgress("[%s|%s] %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("release file creation failed, not a file"),release_file,))
                return 1
            release_string = self.metadata.get('release_string','')
            release_version = self.metadata.get('release_version','')
            release_desc = self.metadata.get('release_desc','')
            file_string = "%s %s %s\n" % (release_string,release_version,release_desc,)
            try:
                f = open(release_file,"w")
                f.write(file_string)
                f.flush()
                f.close()
            except (IOError,OSError,), e:
                self.Output.updateProgress("[%s|%s] %s: %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("release file creation failed, system error"),release_file,e,))
                return 1

        return 0

    def kill(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("executing kill"),))
        return 0

    def run(self):

        self.Output.updateProgress("[%s|%s] %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("hooks running"),))

        # run inner chroot script
        exec_script = self.metadata.get('inner_chroot_script')
        if exec_script:
            while 1:
                tmp_dir = os.path.join(self.dest_dir,molecule.utils.get_random_number())
                if not os.path.lexists(tmp_dir): break
            os.makedirs(tmp_dir)
            tmp_exec = os.path.join(tmp_dir,"inner_exec")
            if os.path.isfile(exec_script) and os.access(exec_script,os.R_OK):
                shutil.copy2(exec_script,tmp_exec)
                os.chmod(tmp_exec,0755)
                dest_exec = tmp_exec[len(self.dest_dir):]
                if not dest_exec.startswith("/"):
                    dest_exec = "/%s" % (dest_exec,)
                rc = molecule.utils.exec_chroot_cmd([dest_exec], self.dest_dir)
                if rc != 0:
                    self.Output.updateProgress("[%s|%s] %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("inner chroot hook failed"),rc,))
                    return rc

        # run outer chroot script
        exec_script = self.metadata.get('outer_chroot_script')
        if exec_script:
            os.environ['CHROOT_DIR'] = self.source_dir
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("spawning"),[exec_script],))
            rc = molecule.utils.exec_cmd([exec_script])
            if rc != 0:
                self.Output.updateProgress("[%s|%s] %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("outer chroot hook failed"),rc,))
                return rc

        # now remove paths to empty
        empty_paths = self.metadata.get('paths_to_empty',[])
        for mypath in empty_paths:
            mypath = os.path.join(self.dest_dir,mypath)
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("emptying dir"),mypath,))
            if os.path.isdir(mypath):
                molecule.utils.empty_dir(mypath)

        # now remove paths to remove (...)
        remove_paths = self.metadata.get('paths_to_remove',[])
        for mypath in remove_paths:
            mypath = os.path.join(self.dest_dir,mypath)
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("removing dir"),mypath,))
            if not os.path.lexists(mypath): continue
            rc = molecule.utils.remove_path(mypath)
            if rc != 0:
                self.Output.updateProgress("[%s|%s] %s: %s: %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("removal failed for"),mypath,rc,))
                return rc

        self.Output.updateProgress("[%s|%s] %s" % (blue("ChrootHandler"),darkred(self.spec_name),_("hooks completed succesfully"),))
        return 0

class CdrootHandler(GenericHandlerInterface):

    def __init__(self, *args, **kwargs):
        GenericHandlerInterface.__init__(self, *args, **kwargs)

    def pre_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("executing pre_run"),))

        self.Output.updateProgress("[%s|%s] %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("preparing environment"),))
        self.source_chroot = os.path.join(self.metadata['destination_chroot'],"chroot",os.path.basename(self.metadata['source_chroot']))
        self.dest_root = os.path.join(self.Config['destination_livecd_root'],"livecd",os.path.basename(self.metadata['source_chroot']))
        if os.path.isdir(self.dest_root):
            molecule.utils.empty_dir(self.dest_root)
        if not os.path.isdir(self.dest_root):
            os.makedirs(self.dest_root,0755)

        return 0

    def post_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("executing post_run"),))
        return 0

    def kill(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("executing kill"),))
        return 0

    def run(self):

        self.Output.updateProgress("[%s|%s] %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("compressing chroot"),))
        args = [self.Config['chroot_compressor']]
        args.extend(self.Config['chroot_compressor_builtin_args'])
        args.extend(self.metadata.get('extra_mksquashfs_parameters',[]))
        comp_output = self.Config['chroot_compressor_output_file']
        if "chroot_compressor_output_file" in self.metadata:
            comp_output = self.metadata.get('chroot_compressor_output_file')
        args.extend([self.source_chroot,comp_output])
        self.Output.updateProgress("[%s|%s] %s: %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("spawning"),args,))
        rc = molecule.utils.exec_cmd(args)
        if rc != 0:
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("chroot compression failed"),rc,))
            return rc
        self.Output.updateProgress("[%s|%s] %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("chroot compressed successfully"),))

        # merge dir
        merge_dir = self.Config['merge_livecd_root']
        self.Output.updateProgress("[%s|%s] %s %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("merging livecd root"),merge_dir,))
        try:
            shutil.copytree(merge_dir,self.dest_root)
        except shutil.error, e:
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("CdrootHandler"),darkred(self.spec_name),_("error during livecd root copy"),e,))
            return 1

        return 0

class IsoHandler(GenericHandlerInterface):

    def __init__(self, *args, **kwargs):
        GenericHandlerInterface.__init__(self, *args, **kwargs)

    def pre_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("IsoHandler"),darkred(self.spec_name),_("executing pre_run"),))

        # setup paths
        self.source_path = os.path.join(self.Config['destination_livecd_root'],"livecd",os.path.basename(self.metadata['source_chroot']))
        dest_iso_dir = self.metadata['destination_iso_directory']
        if not os.path.isdir(dest_iso_dir):
            os.makedirs(dest_iso_dir,0755)
        dest_iso_filename = self.metadata.get('destination_iso_image_name')
        if not dest_iso_filename:
            dest_iso_filename = "%s_%s_%s.iso" (
                self.metadata.get('release_string','').replace(' ','_'),
                self.metadata.get('release_version','').replace(' ','_'),
                self.metadata.get('release_desc','').replace(' ','_'),
            )
        self.dest_iso = os.path.join(dest_iso_dir,dest_iso_filename)
        self.iso_title = "%s %s %s" % (self.metadata.get('release_string',''), self.metadata.get('release_version',''), self.metadata.get('release_desc',''),)
        self.source_chroot = self.metadata['source_chroot']
        self.chroot_dir = os.path.join(self.metadata['destination_chroot'],"chroot",os.path.basename(self.source_chroot))

        # run outer chroot script
        exec_script = self.metadata.get('pre_iso_script')
        if exec_script:
            os.environ['SOURCE_CHROOT_DIR'] = self.source_chroot
            os.environ['CHROOT_DIR'] = self.chroot_dir
            os.environ['CDROOT_DIR'] = self.source_path
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("IsoHandler"),darkred(self.spec_name),_("spawning"),[exec_script],))
            rc = molecule.utils.exec_cmd([exec_script])
            if rc != 0:
                self.Output.updateProgress("[%s|%s] %s: %s" % (blue("IsoHandler"),darkred(self.spec_name),_("outer chroot hook failed"),rc,))
                return rc

        return 0

    def post_run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("IsoHandler"),darkred(self.spec_name),_("executing post_run"),))
        return 0

    def kill(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("IsoHandler"),darkred(self.spec_name),_("executing kill"),))
        return 0

    def run(self):
        self.Output.updateProgress("[%s|%s] %s" % (blue("IsoHandler"),darkred(self.spec_name),_("building ISO image"),))

        args = [self.Config['iso_builder']]
        args.extend(self.Config['iso_builder_builtin_args'])
        args.extend(self.metadata.get('extra_mkisofs_parameters',[]))
        if self.iso_title.strip():
            args.extend(["-V",self.iso_title])
        args.extend(['-o',self.dest_iso,self.source_path])
        self.Output.updateProgress("[%s|%s] %s: %s" % (blue("IsoHandler"),darkred(self.spec_name),_("spawning"),args,))
        rc = molecule.utils.exec_cmd(args)
        if rc != 0:
            self.Output.updateProgress("[%s|%s] %s: %s" % (blue("IsoHandler"),darkred(self.spec_name),_("ISO image build failed"),rc,))
            return rc

        self.Output.updateProgress("[%s|%s] %s: %s" % (blue("IsoHandler"),darkred(self.spec_name),_("built ISO image"),self.dest_iso,))
        return 0


class Runner(GenericHandlerInterface):

    def __init__(self, spec_path, metadata):
        GenericHandlerInterface.__init__(self, spec_path, metadata)
        self.execution_order = [MirrorHandler,ChrootHandler,CdrootHandler,IsoHandler]

    def pre_run(self):
        return 0

    def post_run(self):
        return 0

    def kill(self):
        return 0

    def run(self):

        self.pre_run()
        count = 0
        maxcount = len(self.execution_order)
        self.Output.updateProgress( "[%s|%s] %s" % (darkgreen("Runner"),brown(self.spec_name),_("preparing execution"),), count = (count,maxcount,))
        for myclass in self.execution_order:

            count += 1
            self.Output.updateProgress( "[%s|%s] %s %s" % (darkgreen("Runner"),brown(self.spec_name),_("executing"),str(myclass),), count = (count,maxcount,))
            my = myclass(self.spec_path, self.metadata)

            rc = 0
            while 1:
                # pre-run
                rc = my.pre_run()
                if rc: break
                # run
                rc = my.run()
                if rc: break
                # post-run
                rc = my.post_run()
                if rc: break
                break

            my.kill()
            if rc: return rc

        self.post_run()
        self.Output.updateProgress( "[%s|%s] %s" % (darkgreen("Runner"),brown(self.spec_name),_("All done"),))
        return 0
