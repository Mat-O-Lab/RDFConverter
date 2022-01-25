FROM maven:3.8-amazoncorretto-8 as maven_builder

COPY src /src/
COPY pom.xml .

RUN mvn package

FROM tomcat:jdk8-corretto

COPY --from=maven_builder /target/rdfconv.war /usr/local/tomcat/webapps

CMD ["catalina.sh", "run"]
