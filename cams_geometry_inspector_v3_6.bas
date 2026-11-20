Option Explicit

' CAMS CATIA V5 Geometry Inspector V3.6
' Read-only inspection of existing CAMS duct CATParts.
' Does not modify source CATParts or create assembly constraints.
'
' Output:
' C:\CAMS_CATIA\output\CAMS_GEOMETRY_INSPECTION_V3_6.txt
'
' Notes:
' - Each inspection item has independent error handling.
' - Sketches are enumerated per Body (not Part.Sketches).
' - Pad-specific properties are attempted defensively. Unsupported
'   Automation properties are reported as WARNING, not fatal errors.
' - Volume is measured through SPAWorkbench. Sketch line endpoints are queried defensively.
' - Solid XYZ bounding box and definitive Pad/Profile linkage remain deferred.

Private gFSO As Object
Private gTS As Object
Private gWarnings As Long
Private gErrors As Long

Public Sub CATMain()
    On Error GoTo FatalError

    Dim baseDir As String
    Dim outDir As String
    Dim outputFile As String
    Dim files As Variant
    Dim keys As Variant
    Dim i As Long
    Dim doc As Object
    Dim openedByMacro As Boolean

    baseDir = "C:\CAMS_CATIA"
    outDir = baseDir & "\output"
    outputFile = outDir & "\CAMS_GEOMETRY_INSPECTION_V3_6.txt"

    Set gFSO = CreateObject("Scripting.FileSystemObject")
    If Not gFSO.FolderExists(baseDir) Then
        gFSO.CreateFolder baseDir
    End If
    If Not gFSO.FolderExists(outDir) Then
        gFSO.CreateFolder outDir
    End If
    Set gTS = gFSO.CreateTextFile(outputFile, True, True)

    gWarnings = 0
    gErrors = 0

    WriteLine "============================================================"
    WriteLine "CAMS CATIA V5 GEOMETRY INSPECTOR V3.6"
    WriteLine "Read-only CATPart / Body / Pad / Sketch coordinate checks"
    WriteLine "============================================================"
    WriteLine "CATIA Version: " & SafeVersion()
    WriteLine "Timestamp: " & CStr(Now)
    WriteLine "Source modification: NOT INTENDED"
    WriteLine ""

    keys = Array("ROW1", "ROW23_COMMON", "ROW2", "ROW3")
    files = Array( _
        outDir & "\CAMS_ROW1.CATPart", _
        outDir & "\CAMS_ROW23_COMMON.CATPart", _
        outDir & "\CAMS_ROW2.CATPart", _
        outDir & "\CAMS_ROW3.CATPart")

    For i = LBound(files) To UBound(files)
        WriteLine ""
        WriteLine "############################################################"
        WriteLine "PART KEY: " & CStr(keys(i))
        WriteLine "FILE: " & CStr(files(i))
        WriteLine "############################################################"

        Set doc = Nothing
        openedByMacro = False

        If gFSO.FileExists(CStr(files(i))) Then
            Set doc = GetOrOpenDocument(CStr(files(i)), openedByMacro)
            If doc Is Nothing Then
                WriteLine "[FAIL] Could not open/find document."
                gErrors = gErrors + 1
            Else
                InspectDocument doc, CStr(keys(i))
            End If
        Else
            WriteLine "[FAIL] File not found."
            gErrors = gErrors + 1
        End If
    Next i

    WriteLine ""
    WriteLine "============================================================"
    WriteLine "INSPECTION SUMMARY"
    WriteLine "Warnings: " & CStr(gWarnings)
    WriteLine "Errors: " & CStr(gErrors)
    WriteLine "INSPECTION COMPLETE"
    WriteLine "Pad-to-Sketch association: NOT CONFIRMED by this version."
    WriteLine "Solid XYZ bounding box: NOT IMPLEMENTED in this version."
    WriteLine "No source CATPart geometry was intentionally modified."
    WriteLine "============================================================"

    gTS.Close
    Set gTS = Nothing
    MsgBox "CAMS V3.6 inspection complete." & vbCrLf & outputFile & vbCrLf & _
           "Warnings: " & CStr(gWarnings) & "  Errors: " & CStr(gErrors), vbInformation
    Exit Sub

FatalError:
    On Error Resume Next
    If Not gTS Is Nothing Then
        WriteLine "[FATAL ERROR] " & Err.Number & " : " & Err.Description
        gTS.Close
    End If
    MsgBox "V3.6 failed: " & Err.Number & " - " & Err.Description, vbCritical
End Sub

Private Function SafeVersion() As String
    On Error Resume Next
    SafeVersion = CStr(CATIA.Version)
    If Err.Number <> 0 Then
        Err.Clear
        SafeVersion = "Unavailable"
    End If
End Function

Private Function GetOrOpenDocument(ByVal fullPath As String, ByRef openedByMacro As Boolean) As Object
    On Error GoTo OpenNew
    Dim d As Object

    For Each d In CATIA.Documents
        Err.Clear
        If LCase(CStr(d.FullName)) = LCase(fullPath) Then
            Set GetOrOpenDocument = d
            openedByMacro = False
            Exit Function
        End If
    Next d

OpenNew:
    Err.Clear
    On Error GoTo Failed
    Set GetOrOpenDocument = CATIA.Documents.Open(fullPath)
    openedByMacro = True
    Exit Function

Failed:
    WriteLine "[OPEN ERROR] " & Err.Number & " : " & Err.Description
    gErrors = gErrors + 1
    Set GetOrOpenDocument = Nothing
End Function

Private Sub InspectDocument(ByVal doc As Object, ByVal partKey As String)
    On Error GoTo DocError

    Dim part As Object
    Dim bodies As Object
    Dim body As Object
    Dim shapes As Object
    Dim shp As Object
    Dim i As Long
    Dim j As Long
    Dim sketchCount As Long

    WriteLine "Document.Name: " & SafeString(doc.Name)
    WriteLine "Document.FullName: " & SafeString(doc.FullName)

    Set part = doc.Part
    WriteLine "Part.Name: " & SafeString(part.Name)

    Set bodies = part.Bodies
    WriteLine "Part.Bodies.Count: " & CStr(bodies.Count)

    For i = 1 To bodies.Count
        Set body = Nothing
        Set body = bodies.Item(i)
        WriteLine ""
        WriteLine "  BODY[" & CStr(i) & "]: " & SafeString(body.Name)

        InspectBodyMeasurement doc, part, body, i

        Set shapes = Nothing
        On Error Resume Next
        Err.Clear
        Set shapes = body.Shapes
        If Err.Number <> 0 Or shapes Is Nothing Then
            WriteLine "    [WARNING] Body.Shapes unavailable: " & Err.Number & " - " & Err.Description
            gWarnings = gWarnings + 1
            Err.Clear
        Else
            WriteLine "    Shapes.Count: " & CStr(shapes.Count)
            For j = 1 To shapes.Count
                Set shp = Nothing
                Err.Clear
                Set shp = shapes.Item(j)
                If Err.Number <> 0 Or shp Is Nothing Then
                    WriteLine "    [WARNING] Cannot retrieve Shape[" & CStr(j) & "]"
                    gWarnings = gWarnings + 1
                    Err.Clear
                Else
                    InspectShape shp, j
                End If
            Next j
        End If
        On Error GoTo DocError

        InspectBodySketches body, i, sketchCount
    Next i

    WriteLine ""
    WriteLine "  Total Sketches found through Body.Sketches: " & CStr(sketchCount)
    Exit Sub

DocError:
    WriteLine "[DOCUMENT ERROR] " & Err.Number & " : " & Err.Description
    gErrors = gErrors + 1
    Err.Clear
End Sub

Private Sub InspectShape(ByVal shp As Object, ByVal index As Long)
    Dim v As Variant
    Dim obj As Object
    Dim typeText As String

    On Error Resume Next
    typeText = TypeName(shp)
    WriteLine "    SHAPE[" & CStr(index) & "] Name=" & SafeString(shp.Name) & _
              " TypeName=" & typeText

    If InStr(1, typeText, "Pad", vbTextCompare) > 0 Or _
       InStr(1, SafeString(shp.Name), "PAD", vbTextCompare) > 0 Then
        WriteLine "      Pad inspection:"
    Else
        WriteLine "      Feature-specific inspection skipped (not identified as Pad)."
        Exit Sub
    End If

    Err.Clear
    Set obj = Nothing
    Set obj = CallByName(shp, "FirstLimit", VbGet)
    If Err.Number = 0 And Not obj Is Nothing Then
        WriteLine "        FirstLimit object: " & TypeName(obj)
        DumpLimit obj, "FirstLimit"
    Else
        WriteLine "        [WARNING] FirstLimit unavailable: " & CStr(Err.Number) & " - " & Err.Description
        gWarnings = gWarnings + 1
    End If

    Err.Clear
    Set obj = Nothing
    Set obj = CallByName(shp, "SecondLimit", VbGet)
    If Err.Number = 0 And Not obj Is Nothing Then
        WriteLine "        SecondLimit object: " & TypeName(obj)
        DumpLimit obj, "SecondLimit"
    Else
        WriteLine "        [INFO] SecondLimit unavailable/not exposed."
        Err.Clear
    End If

    Err.Clear
    Set obj = Nothing
    Set obj = CallByName(shp, "Profile", VbGet)
    If Err.Number = 0 And Not obj Is Nothing Then
        WriteLine "        Profile.Name: " & SafeString(obj.Name)
        WriteLine "        Profile.TypeName: " & TypeName(obj)
    Else
        WriteLine "        [WARNING] Profile unavailable: " & CStr(Err.Number) & " - " & Err.Description
        gWarnings = gWarnings + 1
    End If

    Err.Clear
    Set obj = Nothing
    Set obj = CallByName(shp, "Direction", VbGet)
    If Err.Number = 0 And Not obj Is Nothing Then
        WriteLine "        Direction.TypeName: " & TypeName(obj)
        WriteLine "        Direction.Name: " & SafeString(obj.Name)
    Else
        WriteLine "        [INFO] Direction property unavailable/not exposed."
        Err.Clear
    End If
End Sub

Private Sub DumpLimit(ByVal limitObj As Object, ByVal label As String)
    On Error Resume Next
    Dim limType As Variant
    Dim dimObj As Object
    Dim val As Variant

    Err.Clear
    limType = CallByName(limitObj, "LimitMode", VbGet)
    If Err.Number = 0 Then
        WriteLine "          " & label & ".LimitMode=" & CStr(limType)
    Else
        WriteLine "          " & label & ".LimitMode unavailable"
    End If

    Err.Clear
    Set dimObj = Nothing
    Set dimObj = CallByName(limitObj, "Dimension", VbGet)
    If Err.Number = 0 And Not dimObj Is Nothing Then
        Err.Clear
        val = CallByName(dimObj, "Value", VbGet)
        If Err.Number = 0 Then
            WriteLine "          " & label & ".Dimension.Value (mm)=" & FormatNumber(CDbl(val), 4)
        Else
            WriteLine "          " & label & ".Dimension.Value unavailable"
            gWarnings = gWarnings + 1
        End If
    Else
        WriteLine "          " & label & ".Dimension unavailable"
        gWarnings = gWarnings + 1
    End If
    Err.Clear
End Sub

Private Sub InspectBodySketches(ByVal body As Object, ByVal bodyIndex As Long, ByRef totalSketches As Long)
    On Error Resume Next
    Dim sketches As Object
    Dim sk As Object
    Dim i As Long

    Err.Clear
    Set sketches = Nothing
    Set sketches = body.Sketches
    If Err.Number <> 0 Or sketches Is Nothing Then
        WriteLine "    [WARNING] Body.Sketches unavailable: " & Err.Number & " - " & Err.Description
        gWarnings = gWarnings + 1
        Err.Clear
        Exit Sub
    End If

    WriteLine "    Body.Sketches.Count: " & CStr(sketches.Count)
    For i = 1 To sketches.Count
        Set sk = Nothing
        Err.Clear
        Set sk = sketches.Item(i)
        If Err.Number <> 0 Or sk Is Nothing Then
            WriteLine "      [WARNING] Cannot retrieve Sketch[" & CStr(i) & "]"
            gWarnings = gWarnings + 1
            Err.Clear
        Else
            totalSketches = totalSketches + 1
            InspectSketch sk, bodyIndex, i
        End If
    Next i
End Sub

Private Sub InspectSketch(ByVal sk As Object, ByVal bodyIndex As Long, ByVal index As Long)
    On Error Resume Next
    Dim geos As Object
    Dim geo As Object
    Dim axisData(8) As Variant
    Dim i As Long
    Dim lineCount As Long
    Dim okLines As Long
    Dim minX As Double, minY As Double
    Dim maxX As Double, maxY As Double
    Dim gotAny As Boolean

    WriteLine "      SKETCH[B" & CStr(bodyIndex) & "-" & CStr(index) & "]: " & SafeString(sk.Name)

    ' CATIA returns the sketch absolute axis through a 9-element Variant array.
    ' Initialize with sentinels so an unchanged output array is not mistaken for valid zero data.
    For i = 0 To 8
        axisData(i) = 9.87654321E+99
    Next i
    Err.Clear
    sk.GetAbsoluteAxisData axisData
    If Err.Number = 0 Then
        WriteLine "        AbsoluteAxisData diagnostic:"
        For i = 0 To 8
            If IsNumeric(axisData(i)) Then
                If Abs(CDbl(axisData(i))) < 1E+90 Then
                    WriteLine "          A(" & CStr(i) & ")=" & FormatNumber(CDbl(axisData(i)), 6)
                Else
                    WriteLine "          A(" & CStr(i) & ")=<unchanged>"
                End If
            Else
                WriteLine "          A(" & CStr(i) & ")=<non-numeric>"
            End If
        Next i
    Else
        WriteLine "        [WARNING] GetAbsoluteAxisData failed: " & Err.Number & " - " & Err.Description
        gWarnings = gWarnings + 1
        Err.Clear
    End If

    Set geos = Nothing
    Set geos = sk.GeometricElements
    If Err.Number <> 0 Or geos Is Nothing Then
        WriteLine "        [WARNING] GeometricElements unavailable: " & Err.Number & " - " & Err.Description
        gWarnings = gWarnings + 1
        Err.Clear
        Exit Sub
    End If

    WriteLine "        GeometricElements.Count: " & CStr(geos.Count)
    lineCount = 0
    okLines = 0
    gotAny = False

    For i = 1 To geos.Count
        Set geo = Nothing
        Err.Clear
        Set geo = geos.Item(i)
        If Err.Number = 0 And Not geo Is Nothing Then
            WriteLine "          GEO[" & CStr(i) & "] TypeName=" & TypeName(geo) & _
                      " Name=" & SafeString(geo.Name)
            If InStr(1, TypeName(geo), "Line2D", vbTextCompare) > 0 Then
                lineCount = lineCount + 1
                If InspectLine2D(geo, lineCount, minX, minY, maxX, maxY, gotAny) Then
                    okLines = okLines + 1
                End If
            End If
        Else
            WriteLine "          [WARNING] Cannot retrieve geometry element " & CStr(i)
            gWarnings = gWarnings + 1
            Err.Clear
        End If
    Next i

    WriteLine "        Line2D count: " & CStr(lineCount)
    WriteLine "        Line2D endpoint pairs read: " & CStr(okLines)
    If gotAny Then
        WriteLine "        Sketch-local XY extents (CATIA model units):"
        WriteLine "          Xmin=" & FormatNumber(minX, 4) & "  Xmax=" & FormatNumber(maxX, 4)
        WriteLine "          Ymin=" & FormatNumber(minY, 4) & "  Ymax=" & FormatNumber(maxY, 4)
        WriteLine "          Width=" & FormatNumber(maxX - minX, 4) & _
                  "  Height=" & FormatNumber(maxY - minY, 4)
        If okLines <> lineCount Then
            WriteLine "        [WARNING] Some Line2D endpoints could not be read; extents may be incomplete."
            gWarnings = gWarnings + 1
        End If
    Else
        WriteLine "        [WARNING] No valid Line2D endpoint coordinates were obtained."
        gWarnings = gWarnings + 1
    End If
End Sub

Private Function InspectLine2D(ByVal lineObj As Object, ByVal lineIndex As Long, _
                               ByRef minX As Double, ByRef minY As Double, _
                               ByRef maxX As Double, ByRef maxY As Double, _
                               ByRef gotAny As Boolean) As Boolean
    On Error Resume Next
    Dim pStart As Object
    Dim pEnd As Object
    Dim sx As Double, sy As Double, ex As Double, ey As Double
    Dim okStart As Boolean, okEnd As Boolean

    Set pStart = Nothing
    Set pEnd = Nothing

    Err.Clear
    CallByName lineObj, "GetStartPoint", VbMethod, pStart
    If Err.Number = 0 And Not pStart Is Nothing Then
        okStart = ReadPoint2D(pStart, sx, sy)
    End If

    Err.Clear
    CallByName lineObj, "GetEndPoint", VbMethod, pEnd
    If Err.Number = 0 And Not pEnd Is Nothing Then
        okEnd = ReadPoint2D(pEnd, ex, ey)
    End If

    If okStart And okEnd Then
        WriteLine "            LINE[" & CStr(lineIndex) & "] Start=(" & _
                  FormatNumber(sx, 4) & ", " & FormatNumber(sy, 4) & _
                  ") End=(" & FormatNumber(ex, 4) & ", " & FormatNumber(ey, 4) & ")"
        UpdateExtent sx, sy, minX, minY, maxX, maxY, gotAny
        UpdateExtent ex, ey, minX, minY, maxX, maxY, gotAny
        InspectLine2D = True
    Else
        WriteLine "            [WARNING] LINE[" & CStr(lineIndex) & _
                  "] endpoint API unavailable (start=" & CStr(okStart) & _
                  ", end=" & CStr(okEnd) & ")."
        InspectLine2D = False
    End If
    Err.Clear
End Function

Private Function ReadPoint2D(ByVal pointObj As Object, ByRef x As Double, ByRef y As Double) As Boolean
    On Error Resume Next
    Dim vx As Variant, vy As Variant

    Err.Clear
    CallByName pointObj, "GetCoordinates", VbMethod, vx, vy
    If Err.Number = 0 And IsNumeric(vx) And IsNumeric(vy) Then
        x = CDbl(vx)
        y = CDbl(vy)
        ReadPoint2D = True
    Else
        Err.Clear
        ' Some CATIA releases expose X/Y as properties on Point2D.
        vx = CallByName(pointObj, "X", VbGet)
        vy = CallByName(pointObj, "Y", VbGet)
        If Err.Number = 0 And IsNumeric(vx) And IsNumeric(vy) Then
            x = CDbl(vx)
            y = CDbl(vy)
            ReadPoint2D = True
        Else
            ReadPoint2D = False
        End If
    End If
    Err.Clear
End Function

Private Sub UpdateExtent(ByVal x As Double, ByVal y As Double, _
                         ByRef minX As Double, ByRef minY As Double, _
                         ByRef maxX As Double, ByRef maxY As Double, _
                         ByRef gotAny As Boolean)
    If Not gotAny Then
        minX = x: maxX = x
        minY = y: maxY = y
        gotAny = True
    Else
        If x < minX Then minX = x
        If x > maxX Then maxX = x
        If y < minY Then minY = y
        If y > maxY Then maxY = y
    End If
End Sub

Private Sub InspectBodyMeasurement(ByVal doc As Object, ByVal part As Object, ByVal body As Object, ByVal bodyIndex As Long)
    On Error Resume Next
    Dim spa As Object
    Dim ref As Object
    Dim measurable As Object
    Dim xMin As Double
    Dim yMin As Double
    Dim zMin As Double
    Dim xMax As Double
    Dim yMax As Double
    Dim zMax As Double
    Dim vol As Variant

    WriteLine "    Geometry measurement:"

    Err.Clear
    Set spa = doc.GetWorkbench("SPAWorkbench")
    If Err.Number <> 0 Or spa Is Nothing Then
        WriteLine "      [WARNING] SPAWorkbench unavailable: " & Err.Number & " - " & Err.Description
        gWarnings = gWarnings + 1
        Err.Clear
        Exit Sub
    End If

    Err.Clear
    Set ref = part.CreateReferenceFromObject(body)
    If Err.Number <> 0 Or ref Is Nothing Then
        WriteLine "      [WARNING] Cannot create Body reference: " & Err.Number & " - " & Err.Description
        gWarnings = gWarnings + 1
        Err.Clear
        Exit Sub
    End If

    Err.Clear
    Set measurable = spa.GetMeasurable(ref)
    If Err.Number <> 0 Or measurable Is Nothing Then
        WriteLine "      [WARNING] GetMeasurable failed: " & Err.Number & " - " & Err.Description
        gWarnings = gWarnings + 1
        Err.Clear
        Exit Sub
    End If

    ' CATIA V5 SPA Measurable does not expose GetBoundingBox in this
    ' Automation interface. Do not call an unsupported method.
    WriteLine "      [DEFERRED] BoundingBox: not available through this Measurable interface."
    WriteLine "      [INFO] A separate vertex-topology traversal is required for XYZ extents."

    Err.Clear
    vol = CallByName(measurable, "Volume", VbGet)
    If Err.Number = 0 Then
        WriteLine "      Volume=" & FormatNumber(CDbl(vol), 6) & " (CATIA volume units)"
    Else
        WriteLine "      [INFO] Volume property unavailable; solid-volume check not confirmed."
        Err.Clear
    End If
End Sub

Private Function SafeString(ByVal value As Variant) As String
    On Error Resume Next
    SafeString = CStr(value)
    If Err.Number <> 0 Then
        Err.Clear
        SafeString = "<unavailable>"
    End If
End Function

Private Sub WriteLine(ByVal s As String)
    If Not gTS Is Nothing Then
        gTS.WriteLine s
    End If
End Sub
