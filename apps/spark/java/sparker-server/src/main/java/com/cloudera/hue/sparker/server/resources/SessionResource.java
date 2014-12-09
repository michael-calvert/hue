package com.cloudera.hue.sparker.server.resources;

import com.cloudera.hue.sparker.server.sessions.Statement;
import com.cloudera.hue.sparker.server.sessions.ClosedSessionException;
import com.cloudera.hue.sparker.server.sessions.Session;
import com.cloudera.hue.sparker.server.sessions.SessionManager;
import com.codahale.metrics.annotation.Timed;
import com.sun.jersey.core.spi.factory.ResponseBuilderImpl;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import javax.ws.rs.DELETE;
import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
import javax.ws.rs.QueryParam;
import javax.ws.rs.WebApplicationException;
import javax.ws.rs.core.Context;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;
import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeoutException;

@Path("/sessions")
@Produces(MediaType.APPLICATION_JSON)
public class SessionResource {

    private static final String SCALA = "scala";
    private static final String PYTHON = "python";

    private final SessionManager sessionManager;

    public SessionResource(SessionManager sessionManager) {
        this.sessionManager = sessionManager;
    }

    @GET
    @Timed
    public List<String> getSessions() {
        return Collections.list(sessionManager.getSessionIds());
    }

    @POST
    @Timed
    public Response createSession(@QueryParam("lang") String language,
                                  @Context HttpServletRequest request) throws IOException, InterruptedException, URISyntaxException {
        SessionManager.SessionType sessionType;

        if (language == null) {
            Response resp = new ResponseBuilderImpl().status(400).entity("missing language").build();
            throw new WebApplicationException(resp);
        }

        if (language.equals(SCALA)) {
            sessionType = SessionManager.SessionType.SCALA;
        } else if (language.equals(PYTHON)) {
            sessionType = SessionManager.SessionType.PYTHON;
        } else {
            Response resp = new ResponseBuilderImpl().status(400).entity("invalid language").build();
            throw new WebApplicationException(resp);
        }

        Session session = sessionManager.create(sessionType);

        URI location = new URI("/" + session.getId());
        return Response.created(location).build();
    }

    @Path("/{id}")
    @GET
    @Timed
    public List<Statement> getSession(@PathParam("id") String id,
                                 @QueryParam("from") Integer fromCell,
                                 @QueryParam("limit") Integer limit) throws SessionManager.SessionNotFound {
        Session session = sessionManager.get(id);
        List<Statement> statements = session.getStatements();

        if (fromCell != null || limit != null) {
            if (fromCell == null) {
                fromCell = 0;
            }

            if (limit == null) {
                limit = statements.size();
            }

            statements = statements.subList(fromCell, fromCell + limit);
        }

        return statements;
    }

    @Path("/{id}")
    @POST
    @Timed
    public Response executeStatement(@PathParam("id") String id,
                                     @Valid ExecuteStatementRequest body,
                                     @Context HttpServletRequest request) throws Exception, ClosedSessionException, SessionManager.SessionNotFound {
        Session session = sessionManager.get(id);

        // The cell is evaluated inline, but eventually it'll be turned into an asynchronous call.
        Statement statement = session.executeStatement(body.getStatement());

        URI location = new URI("/cells/" + statement.getId());
        return Response.created(location).build();
    }

    @Path("/{id}")
    @DELETE
    @Timed
    public Response closeSession(@PathParam("id") String id) throws InterruptedException, TimeoutException, IOException, SessionManager.SessionNotFound {
        sessionManager.close(id);
        return Response.noContent().build();
    }


    @Path("/{id}/interrupt")
    @POST
    @Timed
    public Response interruptStatement(@PathParam("id") String id) throws SessionManager.SessionNotFound, Session.StatementNotFound, Exception, ClosedSessionException {
        Session session = sessionManager.get(id);

        // FIXME: don't actually do anything for now as it doesn't work yet.
        //  session.interrupt();

        return Response.ok().build();
    }
}
