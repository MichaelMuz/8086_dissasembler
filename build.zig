const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});
    const mod = b.addModule("_8086_dissasembler", .{
        .root_source_file = b.path("src/root.zig"),
        .target = target,
    });

    const integration_test_mod = b.createModule(.{
        .root_source_file = b.path("src/test_root.zig"),
        .target = target,
        .imports = &.{
            .{ .name = "_8086_dissasembler", .module = mod },
        },
    });

    const exe = b.addExecutable(.{
        .name = "_8086_dissasembler",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{
                .{ .name = "_8086_dissasembler", .module = mod },
            },
        }),
    });

    b.installArtifact(exe);

    const run_step = b.step("run", "Run the app");

    const run_cmd = b.addRunArtifact(exe);
    run_step.dependOn(&run_cmd.step);

    run_cmd.step.dependOn(b.getInstallStep());

    if (b.args) |args| {
        run_cmd.addArgs(args);
    }

    const mod_unit_tests = b.addTest(.{
        .root_module = mod,
    });
    const mod_integration_tests = b.addTest(.{
        .root_module = integration_test_mod,
    });

    const run_mod_unit_tests = b.addRunArtifact(mod_unit_tests);
    const run_mod_integration_tests = b.addRunArtifact(mod_integration_tests);

    const exe_unit_tests = b.addTest(.{
        .root_module = exe.root_module,
    });

    const run_exe_unit_tests = b.addRunArtifact(exe_unit_tests);

    const unit_test_step = b.step("unit", "Run unit tests");
    unit_test_step.dependOn(&run_mod_unit_tests.step);
    unit_test_step.dependOn(&run_exe_unit_tests.step);

    const integration_test_step = b.step("integration", "Run integration tests");
    integration_test_step.dependOn(&run_mod_integration_tests.step);

    const all_test_step = b.step("test", "Run all tests");
    all_test_step.dependOn(integration_test_step);
    all_test_step.dependOn(unit_test_step);
}
