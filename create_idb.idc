#include <idc.idc>

static main()
{
  // turn on coagulation of data in the final pass of analysis
  set_inf_attr(INF_AF, get_inf_attr(INF_AF) | AF_DODATA | AF_FINAL);
  // .. and plan the entire address space for the final pass
  auto_mark_range(0, BADADDR, AU_FINAL);

  msg("Waiting for the end of the auto analysis...\n");
  auto_wait();

  msg("All done, exiting...\n");

  // the following line instructs IDA to quit without saving the database
  // process_config_directive("ABANDON_DATABASE=YES");

  qexit(0); // exit to OS, error code 0 - success
}
