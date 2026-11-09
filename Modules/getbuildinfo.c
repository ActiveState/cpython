#include "Python.h"

#ifndef DONT_HAVE_STDIO_H
#include <stdio.h>
#endif

#ifndef DATE
#ifdef __DATE__
#define DATE __DATE__
#else
#define DATE "xx/xx/xx"
#endif
#endif

#ifndef TIME
#ifdef __TIME__
#define TIME __TIME__
#else
#define TIME "xx:xx:xx"
#endif
#endif

/* XXX Only unix build process has been tested */
#ifndef GITVERSION
#define GITVERSION ""
#endif
#ifndef GITTAG
#define GITTAG ""
#endif
#ifndef GITBRANCH
#define GITBRANCH ""
#endif

const char *
Py_GetBuildInfo(void)
{
    static char buildinfo[50 + sizeof("ActiveState ") +
                          sizeof(PY_ACTIVESTATE_VERSION) + sizeof(GITVERSION) +
                          ((sizeof(GITTAG) > sizeof(GITBRANCH)) ?
                           sizeof(GITTAG) : sizeof(GITBRANCH))];
    const char *revision = _Py_gitversion();
    const char *sep = *revision ? ":" : "";
    const char *gitid = _Py_gitidentifier();
    if (!(*gitid) && *revision) {
        gitid = "main";
    }
    /* The ActiveState release leads the build number field, which has no
       commas: platform._sys_version() parses at most three fields here. */
    PyOS_snprintf(buildinfo, sizeof(buildinfo),
                  "ActiveState %s%s%s%s%s, %.20s, %.9s",
                  PY_ACTIVESTATE_VERSION, *gitid ? " " : "", gitid,
                  sep, revision, DATE, TIME);
    return buildinfo;
}

const char *
_Py_gitversion(void)
{
    return GITVERSION;
}

const char *
_Py_gitidentifier(void)
{
    const char *gittag, *gitid;
    gittag = GITTAG;
    if ((*gittag) && strcmp(gittag, "undefined") != 0)
        gitid = gittag;
    else
        gitid = GITBRANCH;
    return gitid;
}
